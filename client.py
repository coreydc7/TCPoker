import asyncio
import json
import logging
import argparse
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
        
    async def update_state(self, new_state):
        if new_state == "lobby":
            self.valid_commands = ['ready', 'status', 'exit']

    async def connect(self):
        ''' First thing a client does is connect to the server and send their custom username '''
        try:
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            logging.info(f"Connected to server at {self.host}:{self.port}")
            await self.send_message({"username": self.username})
            asyncio.create_task(self.receive_messages())        # Receive messages asynchronously above the client input loop
            await self.input_loop()         # Utilizes PromptToolkit for an asynchronous input()
        except Exception as e:
            logging.error(f"Connection failed: {e}")

    async def send_message(self, message):
        ''' Sends a message to server using clients StreamWriter '''
        try:
            self.writer.write((json.dumps(message) + "\n").encode())        # All messages end with '\n' delimiter
            await self.writer.drain()
            logging.info(f"Sent: {message}")
        except Exception as e:
            logging.error(f"Failed to send message: {e}")

    async def receive_messages(self):
        ''' Asyncio task, received messages print above clients input_loop() '''
        try:
            while True:
                data = await self.reader.readline()
                if not data:
                    logging.info("Server closed the connection.")
                    print("Disconnected from server.")
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
        if "status" in message:
            status = message['status']
            print("\nPlayer Status:")
            for name, ready in status.items():
                print(f"{name}: {'Ready' if ready else 'Not Ready'}")
        if "hand" in message:
            print(f"\nYour hand: {', '.join(message['hand'])}")
        if "error" in message:
            print(f"\nError: {message['error']}")

    async def input_loop(self):
        ''' Main clients input loop '''
        with patch_stdout():
            while True:
                try:
                    command = await self.session.prompt_async(f"Enter a command {self.valid_commands}: ")
                    cmd_parts = command.strip().split()
                    if not cmd_parts:
                        continue
                    cmd = cmd_parts[0].lower()
                    if cmd in self.valid_commands:
                        if cmd.startswith("bet"):       # Certain commands must contain two parts, such as "bet 100"
                            if len(cmd_parts) != 2 or not cmd_parts[1].isdigit():
                                print("Usage: bet <amount>")
                                continue
                            await self.send_message({"command": cmd_parts})
                        else:
                            await self.send_message({"command": cmd_parts})
                            if cmd == "exit":
                                print("Exiting game.")
                                self.writer.close()
                                await self.writer.wait_closed()
                                break
                    else:
                        print(f"Unknown command entered: {cmd}.")
                except (EOFError, KeyboardInterrupt):
                    print("\nExiting game.")
                    await self.send_message({"command": "exit"})
                    self.writer.close()
                    await self.writer.wait_closed()
                    break
                except Exception as e:
                    logging.error(f"Input error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TCP Poker Client")
    parser.add_argument('-i', '--ip', type=str, required=True, help='Server IP Address.')
    parser.add_argument('-p', '--port', type=int, required=True, help='Server Port.')
    parser.add_argument('-u', '--username', type=str, required=True, help='Your username.')

    args = parser.parse_args()

    client = TCPokerClient(args.ip, args.port, args.username)
    try:
        asyncio.run(client.connect())
    except KeyboardInterrupt:
        logging.info("Client terminated manually.")