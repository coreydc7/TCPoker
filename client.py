import socket
import argparse
import sys
import logging
import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

def setup_logging():
    logging.basicConfig(
        filename='client.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

async def receive_messages(sock):
    loop = asyncio.get_event_loop()
    while True:
        try:
            data = await loop.sock_recv(sock, 4096)
            if not data:
                print("\nDisconnected from server.")
                return
            print(f"\nServer: {data.decode('utf-8')}")
            sys.stdout.flush()
        except ConnectionResetError:
            print("\nConnection closed by server.")
            return
        except Exception as e:
            print(f"\nError receiving message: {e}")
            return


async def get_user_input(session, valid_commands):
    try:
        with patch_stdout():
            user_input = await session.prompt_async(f"Enter a command {valid_commands}: ")
            return user_input
    except (EOFError, KeyboardInterrupt):
        return 'exit'

async def send_messages(sock, session):
    loop = asyncio.get_event_loop()
    valid_commands = ['ready', 'status', 'exit']
    
    while True:
        try:
            command = await get_user_input(session, valid_commands)
            
            if command == 'exit':
                await loop.sock_sendall(sock, command.encode('utf-8'))
                print("Exiting...")
                return
                
            if command in valid_commands:
                await loop.sock_sendall(sock, command.encode('utf-8'))
                logging.info(f"Sent command: {command}")
            else:
                print(f"Invalid command. Valid commands are: {valid_commands}")
                
        except Exception as e:
            logging.error(f"Failed to send command: {e}")
            print(f"Error sending command: {e}")
            return

async def main():
    parser = argparse.ArgumentParser(description="TCPoker Client")
    parser.add_argument('-i', '--ip', type=str, required=True, help='Server IP Address.')
    parser.add_argument('-p', '--port', type=int, required=True, help='Server Port.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable debug logging.')
    args = parser.parse_args()
    
    setup_logging()
    server_address = (args.ip, args.port)
    
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect_ex(server_address)
        sock.setblocking(False)  # Set socket to non-blocking mode
        logging.info(f"Connected to {server_address}")
        
        session = PromptSession()
        
        receive_task = asyncio.create_task(receive_messages(sock))
        send_task = asyncio.create_task(send_messages(sock, session))
        
        done, pending = await asyncio.wait(
            [receive_task, send_task],
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
        if sock:
            sock.close()
            logging.info(f"Client disconnecting from {server_address}.")
    

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nClient terminated by user")