import asyncio
import socket
from poker_offline import TexasHoldEm
import libserver
import argparse

class GameState:
    def __init__(self, num_players):
        self.connected_clients = []
        self.game = TexasHoldEm(num_players)

    async def broadcast_message(self, message):
        ''' Broadcast a message to all clients connected '''
        if self.connected_clients:
            message_fmt = self.connected_clients[0].create_message(message)
            for client in self.connected_clients:
                client._send_buffer += message_fmt
                await client._write()

def check_game_start():
    if len(game_state.connected_clients) >= 2 and game_state.game.all_players_ready():
        start_game()
        
def start_game():
    print("Starting Texas Hold'em!")
    #game_state.game.play_hand()?

async def handle_client(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"Accepted connection from {addr}")

    message = libserver.Message(reader, writer, addr, game_state, debug)
    game_state.connected_clients.append(message)

    try:
        while True:
            await message.process_events()
            check_game_start()
    except libserver.ClientDisconnectException:
        print(f"Connection closed by {addr}.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

async def main(host, port, num_clients):
    print("listening on", (host, port))
    server = await asyncio.start_server(handle_client, host, port)
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="(help show the user how to run the server)")

    # Supported command-line args
    parser.add_argument('-i', '--ip', type=str, required=True, help='host-ip')
    parser.add_argument('-p', '--port', type=int, required=True, help='port')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed output, such as connection and disconnection events.')
    parser.add_argument('-c', '--connections', type=int, required=True, help='Number of clients required to start game.')

    # Parse command-line args
    args = parser.parse_args()
        
    global debug
    debug = args.verbose
    host = args.ip
    port = args.port
    num_clients = args.connections

    game_state = GameState(num_clients)
    
    asyncio.run(main(host, port, num_clients))