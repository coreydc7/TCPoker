import socket
import selectors
import traceback
import argparse
from poker import TexasHoldEm

import libserver

sel = selectors.DefaultSelector()

# This class holds our instance of TexasHoldEm
class GameState:
    def __init__(self, num_players):
        self.connected_clients = []
        self.game = TexasHoldEm(num_players)
        
    def broadcast_message(self, message):
        ''' Broadcast a message to all clients connected '''
        if len(self.connected_clients) >= 1:
            message_fmt = self.connected_clients[0].create_message(message)
        
            for client in self.connected_clients:   # for each libserver Message (client), append to _send_buffer for _write() method, set to 'w' to trigger method
                client._send_buffer += message_fmt
                client._set_selector_events_mask('w')
        
def check_game_start():
    if len(game_state.connected_clients) >= 2 and game_state.game.all_players_ready():
        start_game()
        
def start_game():
    print("Starting Texas Hold'em!")
    #game_state.game.play_hand()

def accept_wrapper(sock):
    conn, addr = sock.accept()  # Should be ready to read
    print("accepted connection from", addr)
    conn.setblocking(False)
    # Pass game_state into each Message class
    message = libserver.Message(sel, conn, addr, game_state, debug)
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
parser.add_argument('-c', '--connections', type=int, required=True, help='Number of clients required to start game.')

# Parse command-line args
args = parser.parse_args()
    
debug = args.verbose
host = args.ip
port = args.port
numClients = args.connections

game_state = GameState(numClients)


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
                    check_game_start()  # Check if the game should start after each event
                except libserver.ClientDisconnectException:
                    # Handles client disconnections
                    print(f"Connection closed by {message.addr}.")
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