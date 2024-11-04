import asyncio
import json
import logging
import argparse

logging.basicConfig(
    # Configure logging
    filename='server.log',
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
    )

class Player:
    ''' Manages state of each player '''
    def __init__(self, name, writer, stack=1000):
        self.name = name
        self.writer = writer
        self.ready = False
        self.stack = stack  
        self.hand = []

    # def to_dict(self):
    #     return {
    #         "name": self.name,
    #         "ready": self.ready,
    #         "stack": self.stack,
    #         "hand": [str(card) for card in self.hand]
    #     }

class TCPokerServer:
    ''' Manages state of the Poker Game '''
    def __init__(self):
        self.players = []
        self.pot = 0
        self.small_blind = 10
        self.big_blind = 20
        self.deck = self.create_deck()

    def create_deck(self):
        suits = ['♠', '♥', '♦', '♣']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        return [f"{rank}{suit}" for suit in suits for rank in ranks]

    async def handle_client(self, reader, writer):
        ''' Main client event handler '''
        addr = writer.get_extra_info('peername')
        print(f"Accepted new connection from {addr}")
        logging.info(f"Accepted new connection from {addr}")

        # First thing clients do is join by sending their custom username, receive it here
        try:
            data = await reader.readline()      # Respects the '\n' delimiter used by client.py
            message = json.loads(data.decode())
            if "username" not in message:       # Verify first message received from client is "username"
                raise ValueError("Client username not found.")
            player = Player(message["username"], writer)        # Create new Player for connected client
            self.players.append(player)
            logging.info(f"{addr} has chosen the username: {player.name}")
            await self.broadcast({"broadcast": f"{player.name} has joined the game."})      

            # After client has joined the game, sit and wait for client to send commands
            while True:
                data = await reader.readline()
                if not data:
                    break
                message = json.loads(data.decode())
                logging.info(f"Received message from {player.name}: {message}")
                await self.process_message(player, message)     # Process any received messages
        except json.JSONDecodeError:
            logging.error("Invalid JSON received from client.")
        except Exception as e:
            logging.error(f"Error when handling client: {e}")
        finally:
            # Cleanup after 'exit' command or unexpected client disconnect
            print(f"Connection closed for {addr}")
            logging.info(f"Connection closed for {addr}")
            self.players.remove(player)
            await self.broadcast({"broadcast": f"{player.name} has left the game."})
            writer.close()
            await writer.wait_closed()

    async def process_message(self, player, message):
        ''' Processes any commands received after username stage '''
        if "command" in message:
            command = message["command"][0]
            if command == "ready":
                player.ready = True
                await self.broadcast({"broadcast": f"{player.name} is ready."})
                logging.info(f"{player.name} is ready.")
                await self.check_all_ready()        # After a player readies up, check if all clients are ready
            elif command == "status":
                status = {p.name: p.ready for p in self.players}
                await self.send_message(player, {"status": status})
            elif command == "exit":
                return
            elif command.startswith("bet"):
                amount = int(message["command"][1]) if len(message["command"]) > 1 else 0
                self.pot += amount
                player.stack -= amount
                await self.broadcast({"broadcast": f"{player.name} bets ${amount}. Pot is now ${self.pot}."})
                logging.info(f"{player.name} bets ${amount}. Pot: ${self.pot}")
            else:
                await self.send_message(player, {"error": "Unknown command."})
        else:
            await self.send_message(player, {"error": "Invalid message format."})

    async def check_all_ready(self):
        ''' Check if all clients are ready to start the game '''
        if len(self.players) == 2 and all(p.ready for p in self.players):
            await self.start_game()

    async def start_game(self):
        ''' Main Poker game flow'''
        await self.broadcast({"broadcast": "All players are ready. Starting the game!"})
        # Begin by posting blinds
        await self.post_blinds()
        # Then deal hole cards
        await self.deal_hands()
        # Continue with game logic 

    async def post_blinds(self):
        ''' Posts blinds for a 2-player game '''
        small_blind_player = self.players[0]
        big_blind_player = self.players[1]
        self.pot += self.small_blind + self.big_blind
        small_blind_player.stack -= self.small_blind
        big_blind_player.stack -= self.big_blind
        await self.broadcast({
            "broadcast": f"{small_blind_player.name} posts small blind (${self.small_blind}).",
        })
        await self.broadcast({
            "broadcast": f"{big_blind_player.name} posts big blind (${self.big_blind}).",
        })
        logging.info(f"Blinds posted: {small_blind_player.name} (${self.small_blind}), {big_blind_player.name} (${self.big_blind}). Pot: ${self.pot}")

    async def deal_hands(self):
        for player in self.players:
            player.hand = [self.deck.pop(), self.deck.pop()]
            await self.send_message(player, {"hand": player.hand})
            logging.info(f"Dealt to {player.name}: {player.hand}")

    async def broadcast(self, message):
        ''' Send a message to all players '''
        for player in self.players:
            await self.send_message(player, message)

    async def send_message(self, player, message):
        ''' Send a message to a specific player '''
        try:
            player.writer.write((json.dumps(message) + "\n").encode())      # All messages end with '\n' delimiter
            await player.writer.drain()
            logging.info(f"Sent to {player.name}: {message}")
        except Exception as e:
            logging.error(f"Failed to send message to {player.name}: {e}")


async def main():
    parser = argparse.ArgumentParser(description="TCPoker Server")
    parser.add_argument('-i', '--ip', type=str, required=True, help='Host IP Address.')
    parser.add_argument('-p', '--port', type=int, required=True, help='Port to listen on.')
    args = parser.parse_args() 
    
    poker_server = TCPokerServer()
    
    # Start TCP server
    server = await asyncio.start_server(poker_server.handle_client, args.ip, args.port)
    addr = (args.ip, args.port)
    logging.info(f"Server listening on {addr}")
    print(f"Server listening on {addr}")
    
    async with server:
        await server.serve_forever()
    
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server terminated by user.")
        logging.info("Server terminated by user.")