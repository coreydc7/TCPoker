import sys
import socket
import selectors
import traceback
import struct

import libclient

sel = selectors.DefaultSelector()

def create_request(action, value):
    ''' Example json and binary requests '''
    # if action == "search":
    #     return dict(
    #         type="text/json",
    #         encoding="utf-8",
    #         content=dict(action=action, value=value),
    #     )    
    # if action == "negate" or "double": # Step 1.
    #     return dict(
    #         type="binary/custom-client-binary-type",
    #         encoding="binary",
    #         content=struct.pack(">6si", action.encode("utf-8"), int(value)) 
    #     )
    # else:
    #     return dict(
    #         type="binary/custom-client-binary-type",
    #         encoding="binary",
    #         content=bytes(action + value, encoding="utf-8"),
    #     )
        
def start_connection(host, port, request):
    addr = (host, port)
    print("starting connection to", addr)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Creates a socket for server connection
    sock.setblocking(False)
    sock.connect_ex(addr)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    message = libclient.Message(sel, sock, addr, request) # Creates a 'Message' object using the request dictionary
    sel.register(sock, events, data=message) # Initially set to be monitored for read and write events, Once request has been written, modify it to listen for read events only. No longer interested in write events after the request has been sent

if len(sys.argv) != 5:
    print("usage:", sys.argv[0], "<host> <port> <action> <value>")
    sys.exit(1)
    
host, port = sys.argv[1], int(sys.argv[2])
action, value = sys.argv[3], sys.argv[4]
request = create_request(action, value) # creates a dictionary representing the request from the command-line arguments
start_connection(host, port, request) # passes request into start_connection

try:
    while True:
        events = sel.select(timeout=1)
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