import socket
import argparse
import logging
import asyncio
import json
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

def setup_logging():
    ''' Configure logging '''
    logging.basicConfig(
        filename='client.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

class ClientState:
    ''' This class manages the state of the client. 
        During different stages of the game, the valid_commands changes.
        These changes signal an asyncio.Event(), 
        which updates the on-screen prompt with the currently expected commands. '''
        
    def __init__(self):
        self.game_active = False
        self.my_turn = False
        self.valid_commands = []
        self.session = None
        self.state_change_event = asyncio.Event()
        self.current_state = None
        self.name_set = False
    
    def update_state(self, new_state):
        if new_state == "lobby":
            self.game_active = False
            self.my_turn = False
            self.valid_commands = ['ready', 'status', 'exit']
            self.current_state = "lobby"
        elif new_state == "game":
            self.game_active = True
            self.valid_commands = ['check', 'bet', 'fold', 'raise', 'exit']
            self.my_turn = False
            self.current_state = "game"
        elif new_state == "make_bet":
            self.my_turn = True
            self.valid_commands = ['bet']
            self.current_state = "make_bet"
        self.state_change_event.set()   # Notify send_messages task of the state change

async def send_messages(sock, session, state):
    loop = asyncio.get_event_loop()
    state.session = session

    while True:
        try:
            # Wait for a state change before prompting
            await state.state_change_event.wait()
            state.state_change_event.clear()

            # Determine the appropriate prompt based on the current state
            if(not state.name_set):
                prompt_text=f"\nWelcome to TCPoker! What is your name?: "
            elif state.game_active:
                if state.my_turn:
                    prompt_text = f"\nYour turn! Enter a command {state.valid_commands}: "
                else:
                    # Not clients turn, no action required
                    await asyncio.sleep(0.1)
                    continue
            else:
                prompt_text = f"\nEnter a command {state.valid_commands}: "

            # Prompt for user input
            with patch_stdout():
                command = await session.prompt_async(prompt_text)

            # Split commands such as 'bet 100' into parts ['bet', '100'] or 'bet' into ['bet']
            command_parts = command.strip().split()
            
            # Handle user input
            if not state.name_set:
                message = json.dumps({"username": command_parts}) + "\n"
                await loop.sock_sendall(sock, message.encode('utf-8'))
                logging.info(f"Sent username: {message.strip()}")
                state.name_set = True
                state.update_state("lobby")
            elif command == 'exit':
                message = json.dumps({"command": command_parts}) + "\n"
                await loop.sock_sendall(sock, message.encode('utf-8'))
                print("Exiting...")
                return
            elif command_parts[0] in state.valid_commands: 
                        message = json.dumps({"command": command_parts}) + "\n"
                        await loop.sock_sendall(sock, message.encode('utf-8'))
                        logging.info(f"Sent command: {message.strip()}")
                        if state.my_turn:
                            state.my_turn = False   # Reset turn after sending a command
            else:
                print(f"\nInvalid command. Valid commands are: {state.valid_commands}")
                state.update_state(state.current_state)

        except (EOFError, KeyboardInterrupt):
            # Handle client termination gracefully
            message = json.dumps({"command": "exit"}) + "\n"
            await loop.sock_sendall(sock, message.encode('utf-8'))
            print("\nExiting...")
            return
        except Exception as e:
            logging.error(f"Failed to send command: {e}")
            print(f"\Failed to send command: {e}")
            return

async def receive_messages(sock, state):
    loop = asyncio.get_event_loop()
    buffer = ""

    while True:
        try:
            data = await loop.sock_recv(sock, 4096)
            if not data:
                print("\nDisconnected from server.")
                return

            buffer += data.decode('utf-8')
            messages = buffer.split("\n")   # '\n' is used as a de-limiter to handle multiple messages. Do not forget to add \n to the end of messages sent.
            buffer = messages.pop()  # Save the last incomplete message

            for msg in messages:
                if not msg.strip():
                    continue

                try:
                    message = json.loads(msg)
                    logging.info(f"Received message from server: {message}")

                    if "error" in message:
                        print(f"\nError: {message['error']}")
                        state.update_state(state.current_state)
                    elif "broadcast" in message:
                        print(f"\n{message['broadcast']}")
                    elif "status" in message:
                        print(f"\n{message['status']}")
                        state.update_state("lobby")
                    elif "game_start" in message:
                        print(f"\n{message['game_start']}")
                        state.update_state("game")
                    elif "make_bet" in message:
                        print(f"\n{message['make_bet']}")
                        state.update_state("make_bet")
                    
                except json.JSONDecodeError:
                    logging.error(f"Invalid JSON received: {msg}")
        except ConnectionResetError:
            print("\nConnection closed by server.")
            return
        except Exception as e:
            print(f"\nError receiving message: {e}")
            logging.error(f"Error receiving message: {e}")
            return

async def main():
    parser = argparse.ArgumentParser(description="TCPoker Client")
    parser.add_argument('-i', '--ip', type=str, required=True, help='Server IP Address.')
    parser.add_argument('-p', '--port', type=int, required=True, help='Server Port.')
    args = parser.parse_args()

    setup_logging()
    server_address = (args.ip, args.port)
    sock = None
    tasks = []

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect_ex(server_address)
        sock.setblocking(False)  # Set socket to non-blocking mode
        logging.info(f"Connected to {server_address}")

        state = ClientState()
        state.update_state("lobby")  # Initialize state to 'lobby'

        session = PromptSession()

        receive_task = asyncio.create_task(receive_messages(sock, state))
        send_task = asyncio.create_task(send_messages(sock, session, state))
        tasks = [receive_task, send_task]

        done, pending = await asyncio.wait(
            tasks,
            return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    except Exception as e:
        logging.error(f"Error in main loop {e}.")
        print(f"\nError in main loop: {e}")
    finally:    # Cleanup after a client disconnects
        for task in tasks:
            if not task.done():
                task.cancel()
        if sock:
            sock.close()
            logging.info(f"Client disconnecting from {server_address}.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nClient terminated by user")