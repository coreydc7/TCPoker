import sys
import socket
import selectors
import argparse
import libclient
import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
import logging

logging.basicConfig(
    filename='client.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

sel = selectors.DefaultSelector()
all_valid_requests = ['join', 'status', 'ready', 'exit']
valid_requests = ['status', 'ready', 'exit']
client_disconnect = False

async def get_user_input(session):
    while True:
        user_input = await session.prompt_async(f"Enter a command {valid_requests}: ")
        if user_input in valid_requests:
            return user_input
        else:
            print(f"Invalid command. Try {valid_requests}.")

def create_request(action):
    if action in all_valid_requests:
        return dict(
            type="text/json",
            encoding="utf-8",
            content=dict(action=action)
        )
    else:
        print(f"Unrecognized command. Currently supported commands include: {all_valid_requests}")
        sys.exit(1)
        
def initialize_connection(host, port, request):
    addr = (host, port)
    if(debug): 
        print("starting connection to", addr)
        logging.info(f'attempting connection to {addr}')
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Creates a socket for server connection
    sock.setblocking(False)
    try:
        sock.connect_ex(addr)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        message = libclient.Message(sel, sock, addr, request, debug) # Create a 'Message' object using the request dictionary
        sel.register(sock, events, data=message)    # Register file object with selector
        logging.info(f'successfully initialized connected to {addr}')
        return message
    except socket.error as e:
        print(f"Socket error occurred: {e}")
        logging.info(f"Socket error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        logging.info((f"An unexpected error occurred: {e}"))
    

async def handle_server_messages(message):
    global client_disconnect
    while not client_disconnect:
        events = sel.select(timeout=0)
        for key, mask in events:
            try:
                message.process_events(mask)
                if message.response:
                    message.response = None
            except Exception as e:
                print(f"\nError: {e}")
                logging.error(f'Error processing server message: {e}')
                message.close()
                return
        await asyncio.sleep(0.1)
        
    
async def handle_client_input(message, session):
    global client_disconnect
    while not client_disconnect:
        with patch_stdout():
            user_input = await get_user_input(session)
        request = create_request(user_input)
        message.request = request
        message._request_queued = False
        message._set_selector_events_mask('w')
        if user_input == 'exit':
            client_disconnect = True
    # When client disconnects, close connection and cleanup
    message.close()
    sel.close()
                
async def main():
    parser = argparse.ArgumentParser(description="(help show the player how to connect, and play)")

    # Supported command-line args
    parser.add_argument('-i', '--ip', type=str, required=True, help='IP Address of Server to connect to.')
    parser.add_argument('-p', '--port', type=int, required=True, help='Listening port of Server')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed output, such as connection and disconnection events.')

    # Parse command-line args
    args = parser.parse_args()

    global debug 
    debug = args.verbose
    host = args.ip
    port = args.port  

    # Sends initial join request
    request = create_request('join')
    message = initialize_connection(host, port, request) # passes request into start_connection

    # Initialize PromptSession, a basic command line UI
    session = PromptSession()
    
    server_task = asyncio.create_task(handle_server_messages(message))
    await asyncio.sleep(0.1)
    user_task = asyncio.create_task(handle_client_input(message, session))
    
    await asyncio.gather(server_task, user_task)
    
    logging.info(f"Client disconnecting from {(host, port)}")
    sel.close()
    
if __name__ == "__main__":
    asyncio.run(main())