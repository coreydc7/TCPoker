import socket
import argparse
import sys
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
    def __init__(self):
        self.game_active = False
        self.my_turn = False
        self.valid_commands = []
        self.session = None
        
    def update_state(self, new_state):
        if new_state == "lobby":
            self.game_active = False
            self.my_turn = False
            self.valid_commands = ['ready', 'status', 'exit']
        elif new_state == "game":
            self.game_active = True
            self.valid_commands = ['check', 'bet', 'fold', 'raise', 'exit']
            self.my_turn = False
        elif new_state == "your_turn":
            self.my_turn = True
            self.valid_commands = ['check', 'bet', 'fold', 'raise', 'exit']

async def send_messages(sock, session, state):
    loop = asyncio.get_event_loop()
    state.session = session
    
    while True:
        try:
            if state.game_active:
                # Game started phase
                if state.my_turn:
                    try:
                        with patch_stdout():
                            command = await session.prompt_async(f"\nYour turn! Enter a command {state.valid_commands}: ")
                        message = json.dumps({"command": command})
                        await loop.sock_sendall(sock, message.encode('utf-8'))
                        logging.info(f"Sent game command: {message}")
                        state.my_turn = False   # Ensure only one command is sent per turn
                    except (EOFError, KeyboardInterrupt):
                        return
                else:
                    # Sleep briefly when not player's turn
                    await asyncio.sleep(0.1)
            else:
                # Lobby phase
                try:
                    with patch_stdout():
                        command = await session.prompt_async(f"\nEnter a command {state.valid_commands}: ")
                        
                    if command == 'exit':
                        message = json.dumps({"command": command})
                        await loop.sock_sendall(sock, message.encode('utf-8'))
                        print("Exiting...")
                        return
                    elif command in state.valid_commands:
                        message = json.dumps({"command": command})
                        await loop.sock_sendall(sock, message.encode('utf-8'))
                    else:
                        print(f"\nInvalid command. Valid commands are: {state.valid_commands}")
                except (EOFError, KeyboardInterrupt):
                    return
        except Exception as e:
            logging.error(f"Failed to send command: {e}")
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
            messages = buffer.split("\n")
            buffer = messages.pop()
            
            for msg in messages:
                if not msg:
                    continue
                
                try:
                    message = json.loads(msg)
                    logging.info(f"Received message from server: {message}")
                    
                    if "error" in message:
                        print(f"\nError: {message['error']}")
                    elif "broadcast" in message:
                        print(f"\n{message['broadcast']}")
                    elif "game_start" in message:
                        print(f"\n{message['game_start']}")
                        
                        state.update_state("game")
                    
                    elif "your_turn" in message:
                        print("\nIt is now your turn!")
                        
                        state.update_state("your_turn")
                except json.JSONDecodeError:
                    logging.error(f"Invalid JSON received: {msg}")
        except ConnectionResetError:
            print("\nConnection closed by server.")
            return
        except Exception as e:
            print(f"\nError receiving message: {e}")
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
        state.update_state("lobby")
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
            try: await task
            except asyncio.CancelledError: pass
            
    except Exception as e:
        logging.error(f"Error in main loop {e}.")
        print(f"\nError in main loop {e}.")
    finally:
        # Cleanup after a client disconnects
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