import asyncio
import json
import logging
import argparse
import sys
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout


logging.basicConfig(
    # Configure logging
    filename='client.log',
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
    )


class TCPokerClient:
    ''' Manages client state '''
    def __init__(self, host, port, username):
        self.host = host
        self.port = port
        self.username = username
        self.reader = None
        self.writer = None
        self.session = PromptSession()
        self.valid_commands = ['ready', 'status', 'exit']
        self.game_started = False
        self.refresh_prompt_event = asyncio.Event() 
        
        
    async def connect(self):
        ''' First thing a client does is connect to the server and send their custom username '''
        try:
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            logging.info(f"Connected to server at {self.host}:{self.port}")
            await self.send_message({"username": self.username})
            
            self.refresh_prompt_event.set()
            
            # Start tasks for receiving messages and handling user input
            receive_task = asyncio.create_task(self.receive_messages())        # Receive messages asynchronously above the client input loop
            input_task = asyncio.create_task(self.input_loop())        # Utilizes PromptToolkit for an asynchronous input()
            await asyncio.gather(receive_task, input_task)
        except Exception as e:
            logging.error(f"Connection failed: {e}")


    async def send_message(self, message):
        ''' Sends a message to server using clients StreamWriter '''
        try:
            self.writer.write((json.dumps(message) + "\n").encode())        # All messages end with '\n' delimiter
            await self.writer.drain()
            logging.info(f"{self.username} Sent: {message}")
        except Exception as e:
            logging.error(f"Failed to send message: {e}")


    async def receive_messages(self):
        ''' Asyncio task, received messages print above clients input_loop() '''
        try:
            while True:
                data = await self.reader.readline()
                if not data:
                    # If the server exits
                    logging.info("Server closed the connection.")
                    print("Disconnected from server.")
                    await asyncio.sleep(1)
                    sys.exit(1)
                    break
                message = json.loads(data.decode())
                logging.info(f"{self.username} received message: {message}")
                await self.handle_message(message)      # Handle received messages
        except Exception as e:
            logging.error(f"Error receiving message: {e}")


    async def handle_message(self, message):
        ''' Handles any received messages '''
        if "broadcast" in message:
            print(f"\n{message['broadcast']}")

        elif "status" in message:
            status = message['status']
            print("\nPlayer Status:")
            for name, ready in status.items():
                print(f"{name}: {'Ready' if ready else 'Not Ready'}")

        elif "hand" in message:
            print(f"\nYour hand: ")
            await self.print_cards(message['hand'])

        elif "stack" in message:
            print(f"\n You have: ${message['stack']}")

        elif "error" in message:
            print(f"\nError: {message['error']}")

        elif "start_game" in message:
            self.game_started = True

        elif "action" in message:
            if message["action"] == "collect_ante":
                print(f"\nYou must bet atleast the ante ({message['amount']}) to participate in this hand.")
                self.valid_commands = ['ante']

            elif message["action"] == "collect_bets":
                print(f"\nIt's your turn!\nThe pot is ${message['pot']}\nThe current bet is ${message['current_bet']}")
                self.valid_commands = message["valid_actions"]

            elif message["action"] == "collect_hands":
                print(f"\nTime to send your best 5-card Poker hand!\nChoose 5 cards from your hand (h1, h2) and the community cards (c1, c2, c3, c4, c5)\nExample command format: hand c1 c2 c3 h1 h2")
                self.valid_commands = ['hand']

            elif message["action"] == "clear_prompt":
                self.valid_commands = []

        elif "game_state" in message:
            if message["game_state"] == "lobby":
                print("\nReturning to lobby...")
                self.game_started = False
                self.valid_commands = ['ready', 'status', 'exit']
        
        elif "community_cards" in message:
            print(f"\nCommunity cards: ")
            await self.print_cards(message['community_cards'])
                
        # Update and refresh the prompt message
        self.session.message = f"Enter a command {self.valid_commands}: "
        self.session.app.invalidate()   
        self.refresh_prompt_event.set()       
                

    async def prompt_user(self):
        ''' Prompts the user for input '''
        command = await self.session.prompt_async(f"Enter a command {self.valid_commands}: ")
        await self.process_command(command)
    
        
    async def process_command(self, command):
        ''' Process the user's command '''
        cmd_parts = command.strip().split()
        cmd = cmd_parts[0].lower()
        
        if cmd in self.valid_commands:
            
            if cmd.startswith("ante"):   # Certain commands must contain two parts, such as "bet 100"
                
                if len(cmd_parts) != 2 or not cmd_parts[1].isdigit():
                    print("Usage: ante <amount>")
                    self.refresh_prompt_event.set()
                    return
                await self.send_message({"command": cmd_parts})
            
            elif cmd.startswith("hand"):

                if len(cmd_parts) != 6:
                    print(f"Choose 5 cards. Community cards (c1-c5). Hole cards (h1-h2).\nExample command: hand c1 c2 c3 h1 h2")
                    self.refresh_prompt_event.set()
                    return
                await self.send_message({"command": cmd_parts})
            
            else:
                await self.send_message({"command": cmd_parts})
                
            if cmd == 'exit':
                print("Exiting game.")
                self.writer.close()
                await self.writer.wait_closed()
        
        else:
            print(f"Unknown command entered: {cmd}")
            self.refresh_prompt_event.set()
            

    async def input_loop(self):
        ''' Client input loop task '''
        with patch_stdout():
            while True:
                await self.refresh_prompt_event.wait()
                self.refresh_prompt_event.clear()
                await self.prompt_user()


    async def print_cards(self, cards):
        ''' Creates ASCII art for cards '''
        card_template = [
            ' ___ ',
            '|{} |',
            '| {} |',
            '|_{}|'
        ]

        formatted_cards = []
        for card in cards:
            rank = card[0]
            suit = card[1]
            # pad single digit ranks 
            rank_top = f'{rank} '
            rank_bot = f'_{rank}' 
            formatted_cards.append((rank_top, suit, rank_bot))

        # Print each row for all cards
        for row_idx in range(len(card_template)):
            for card in formatted_cards:
                if row_idx == 0:
                    print(card_template[row_idx], end=' ')
                elif row_idx == 1:
                    print(card_template[row_idx].format(card[0]), end=' ')
                elif row_idx == 2:
                    print(card_template[row_idx].format(card[1]), end=' ')
                else:
                    print(card_template[row_idx].format(card[2]), end=' ') 
            print()



if __name__ == "__main__":
    username = input("Enter your username: ")
    parser = argparse.ArgumentParser(description="TCP Poker Client")
    parser.add_argument('-i', '--ip', type=str, required=True, help='Server IP Address.')
    parser.add_argument('-p', '--port', type=int, required=True, help='Server Port.')

    args = parser.parse_args()

    client = TCPokerClient(args.ip, args.port, username)
    try:
        asyncio.run(client.connect())
    except KeyboardInterrupt:
        logging.info("Client terminated manually.")
        print("\nClient terminated manually.")