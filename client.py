import sys
import socket
import selectors
import traceback
import argparse

import libclient

sel = selectors.DefaultSelector()


valid_requests = ['join','status']
def create_request(action):
    if action in valid_requests:
        return dict(
            type="text/json",
            encoding="utf-8",
            content=dict(action=action)
        )
    else:
        print("Unrecognized command. try 'join' to sit at the table, or 'status' to view the status of the table.")
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

debug = False
if(args.verbose):
    debug = True
host = args.ip
port = args.port  


request = create_request('join')
initialize_connection(host, port, request) # passes request into start_connection

try:
    while True:
        events = sel.select(timeout=1) # repeatedly executes on the 'timeout' interval
        for key, mask in events:
            message = key.data
            try:
                message.process_events(mask)
            except Exception:
                print(
                    "main: error: exception for",
                    f"{message.addr}:\n{traceback.format_exc()}",
                )
                message.close()
        # Check for a socket being monitored to continue.
        if not sel.get_map():
            break
except KeyboardInterrupt:
    print("caught keyboard interrupt, exiting")
finally:
    sel.close()