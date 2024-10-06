import sys
import socket
import selectors
import traceback
import argparse

import libserver

sel = selectors.DefaultSelector()

def accept_wrapper(sock):
    conn, addr = sock.accept()  # Should be ready to read
    print("accepted connection from", addr)
    conn.setblocking(False)
    message = libserver.Message(sel, conn, addr, debug)
    ''' Associates a message object with a socket, initially set to be monitored 
    for read events only. Once its been read, we'll modify it to listen for 
    write events only '''
    sel.register(conn, selectors.EVENT_READ, data=message) 
    
''' Entry point into server.py '''
parser = argparse.ArgumentParser(description="(help show the user how to run the server)")

# Supported command-line args
parser.add_argument('-i', '--ip', type=str, required=True, help='host-ip')
parser.add_argument('-p', '--port', type=int, required=True, help='port')
parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed output, such as connection and disconnection events.')

# Parse command-line args
args = parser.parse_args()
    
debug = False
if(args.verbose):
    debug = True
host = args.ip
port = args.port

lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Avoid bind() exception: OSError: [Errno 48] Address already in use
lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
lsock.bind((host, port))
lsock.listen()
print("listening on", (host, port))
lsock.setblocking(False)
sel.register(lsock, selectors.EVENT_READ, data=None)

try:
    while True:
        events = sel.select(timeout=None)
        for key, mask in events:
            if key.data is None:
                accept_wrapper(key.fileobj)
            else:
                message = key.data
                try:
                    message.process_events(mask)    # Main entry point, will be called repeatedly (Use state variables for things that should only be called once)
                except Exception:
                    print(
                        "main: error: exception for",
                        f"{message.addr}:\n{traceback.format_exc()}",
                    )
                    message.close() # Makes sure that socket is closed upon an exception, also removes the socket from being monitored by select()
except KeyboardInterrupt:
    print("caught keyboard interrupt, exiting")
finally:
    sel.close()