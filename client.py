import socket
import argparse
import sys
import logging
import asyncio
import json
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

game_active = False
my_turn = False

def setup_logging():
    ''' Configure logging '''
    logging.basicConfig(
        filename='client.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

async def receive_messages(sock):
    ''' Asynchronous task that handles receiving messages '''
    global game_active, my_turn
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
            buffer = messages.pop()     # Currently, incomplete messages stay in buffer
            
            for msg in messages:
                if not msg:  # Skip empty messages
                    continue
                
                try:
                    message = json.loads(msg)
                    logging.info(f"Received message from server: {message}")
            
                    if "error" in message:
                        print(f"Error: {message['error']}")
                        continue
                    elif "broadcast" in message:
                        print(message["broadcast"])
                    elif "game_start" in message:
                        game_active = True
                        print(message["game_start"])
                    elif "your_turn" in message:
                        my_turn = True
                        print("It is now your turn!")
                except json.JSONDecodeError:
                    logging.error(f"Invalid JSON received: {msg}")
                    print(f"Invalid JSON received: {msg}")
                        
        except ConnectionResetError:
            print("\nConnection closed by server.")
            return
        except Exception as e:
            print(f"\nError receiving message: {e}")
            return


async def get_user_input(session, valid_commands):
    ''' Asynchronous console input gathering '''
    try:
        with patch_stdout():
            user_input = await session.prompt_async(f"Enter a command {valid_commands}: ")
            return user_input
    except (EOFError, KeyboardInterrupt):
        return 'exit'

async def send_messages(sock, session):
    ''' Asynchronously handles sending messages to the server, depening on if game_active and if my_turn '''
    global game_active, my_turn
    loop = asyncio.get_event_loop()
    
    while True:
        try:
            if game_active:
                # Game phase, only prompt when its clients turn
                if my_turn:
                    valid_game_commands = ['check', 'bet', 'fold', 'raise', 'exit']
                    command = await get_user_input(session, valid_game_commands)
                    message = json.dumps({"command": command})
                    await loop.sock_sendall(sock, message.encode('utf-8'))
                    logging.info(f"Sent game command: {message}")
                    my_turn = False
                else:
                    await asyncio.sleep(0.1)
            else:
                # Lobby phase, continuously prompt for input
                valid_lobby_commands = ['ready', 'status', 'exit']
                command = await get_user_input(session, valid_lobby_commands)
                message = json.dumps({"command": command})
                
                if command == 'exit':
                    await loop.sock_sendall(sock, message.encode('utf-8'))
                    print("Exiting...")
                    return
                elif command in valid_lobby_commands:
                    await loop.sock_sendall(sock, message.encode('utf-8'))
                    logging.info(f"Sent message: {message}")
                else:
                    print(f"Invalid command. Valid commands are: {valid_lobby_commands}")
        except Exception as e:
            logging.error(f"Failed to send command: {e}")
            print(f"Error sending command: {e}")
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
        
        session = PromptSession()
        
        receive_task = asyncio.create_task(receive_messages(sock))
        send_task = asyncio.create_task(send_messages(sock, session))
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
        print(f"Error in main loop {e}.")
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