import sys
import socket
import selectors
import traceback
import argparse
import libclient

sel = selectors.DefaultSelector()
valid_requests = ['join','status', 'ready', 'exit']

def create_request(action):
    if action in valid_requests:
        return dict(
            type="text/json",
            encoding="utf-8",
            content=dict(action=action)
        )
    else:
        print(f"Unrecognized command. Currently supported commands include: {valid_requests}")
        sys.exit(1)
        
def initialize_connection(host, port, request):
    addr = (host, port)
    if(debug): print("starting connection to", addr)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Creates a socket for server connection
    sock.setblocking(False)
    sock.connect_ex(addr)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    message = libclient.Message(sel, sock, addr, request, debug) # Create a 'Message' object using the request dictionary
    sel.register(sock, events, data=message)    # Register file object with selector


''' Entry point into client.py '''
parser = argparse.ArgumentParser(description="(help show the player how to connect, and play)")

# Supported command-line args
parser.add_argument('-i', '--ip', type=str, required=True, help='IP Address of Server to connect to.')
parser.add_argument('-p', '--port', type=int, required=True, help='Listening port of Server')
parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed output, such as connection and disconnection events.')

# Parse command-line args
args = parser.parse_args()

debug = args.verbose
host = args.ip
port = args.port  

# Sends initial join request
request = create_request('join')
initialize_connection(host, port, request) # passes request into start_connection

should_exit = False

try: 
    while not should_exit:
        events = sel.select(timeout=1) # repeatedly executes on the 'timeout' interval
        for key, mask in events:
            message = key.data
            try:
                message.process_events(mask)
                ''' After process_events(), the client checks if there is currently a response. 
                    If there is, then initial connection is complete, and it prompts for user-input for the next (request -> response)
                    TODO: In the future, clients should only be prompted for input when it's their turn to make a move.
                          Consider adding a field to all responses indicating if its time to communicate, by checking message.response.get("ready")'''
                if message.response:    
                    user_input = input(f"Enter command {valid_requests}:").strip()
                    if user_input in valid_requests:
                        request = create_request(user_input)
                        message.request = request
                        message._request_queued = False
                        message.response = None
                        if(user_input == 'exit'): 
                            should_exit = True
                            break
                    else:
                        print(f"Invalid command. Try {valid_requests}.")
            except Exception:
                print(
                    "main: error: exception for",
                    f"{message.addr}:\n{traceback.format_exc()}",
                )
                message.close()

        # # Check for a socket being monitored to continue.
        # if not sel.get_map():
        #     break
except KeyboardInterrupt:
    print("caught keyboard interrupt, exiting")
finally:
    sel.close()