import asyncio
import argparse
import logging
import json
from poker import TexasHoldEm

def setup_logging():
    ''' Configure logging '''
    logging.basicConfig(
        filename='server.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

class GameState:
    ''' Controls Server state and Game state '''
    def __init__(self, num_players):
        self.connected_clients = []
        self.num_players = num_players
        self.ready_status = [False] * num_players
        self.lock = asyncio.Lock()
        self.game = TexasHoldEm(num_players, self)
        self.game_active = False
        
    async def add_client(self, writer, address):
        ''' Handles adding a client to list of connected clients '''
        async with self.lock:
            if len(self.connected_clients) < self.num_players:
                self.connected_clients.append((writer, address))
                self.ready_status[len(self.connected_clients)-1] = False
                print(f"{address} has connected to the game as Player {self.connected_clients.index((writer, address))}.")
                await self.broadcast("broadcast", f"{address} has joined the game as Player {self.connected_clients.index((writer, address))}.")
                logging.info(f"{address} joined the game.")
                return len(self.connected_clients)
            else:
                message = json.dumps({"error": "Unable to join: table is full."}) + '\n'
                writer.write(message.encode('utf-8'))
                await writer.drain()
                logging.info(f"{address} attempted to join but the table was full.")
                return None
                
    async def remove_client(self, writer, address):
        ''' Removes a client from the list of connected clients '''
        async with self.lock:
            for i, (w, addr) in enumerate(self.connected_clients):
                if w == writer:
                    del self.connected_clients[i]
                    del self.ready_status[i]
                    print(f"{address} has disconnected.")
                    await self.broadcast("broadcast", f"Player {i + 1} has left the game.")
                    logging.info(f"{address} disconnected.")
                    break
            if(self.game_active and len(self.connected_clients) == 0):
                print("All players have left, stopping game.")
                logging.info("All players have left, stopping game.")
                self.game_active = False
                self.game.reset_game()
                
    async def broadcast(self, key, value):
        ''' Writes a JSON message to all connected clients, using {key:message} '''
        for writer, addr in self.connected_clients:
            try:
                message = json.dumps({key: value}) + "\n"   # New-line delimiter
                writer.write(message.encode('utf-8'))
                await writer.drain()
            except Exception as e:
                print(f"Failed to send message to {addr}: {e}")
                logging.error(f"Failed to send message to {addr}: {e}")
                
    async def set_ready(self, writer, address):
        ''' Marks a client as ready, checks for readiness to start game '''
        async with self.lock:
            for i, (w, addr) in enumerate(self.connected_clients):
                if w == writer:
                    self.ready_status[i] = True
                    await self.broadcast("broadcast", f"Player {self.connected_clients.index((writer, address))} is ready.")
                    logging.info(f"{address} is ready.")
                    if all(self.ready_status):
                        await self.start_game()
                    break
    
    async def start_game(self):
        await self.broadcast("game_start", "All players are ready. Starting Texas Hold'em!")
        await asyncio.sleep(0.1)      # Always add a small delay in-between messages for proper sequencing
        logging.info("All players are ready. Starting game.")
        self.game_active = True
        
        await self.game.play_hand()   # Starts the main game flow
    
    async def notify_turn(self, current_player):
        ''' Notifies the current player it's their turn '''
        writer, addr = self.connected_clients[current_player]
        try:
            message = json.dumps({"your_turn": True}) + "\n"
            writer.write(message.encode('utf-8'))
            await writer.drain()
            logging.info(f"Notified player {current_player + 1} it's their turn.")
        except Exception as e:
            logging.error(f"Failed to notify player {current_player + 1}: {e}")

async def handle_client(reader, writer, game_state):
    ''' Main client event handler '''
    address = writer.get_extra_info('peername')
    player_number = await game_state.add_client(writer, address)
    
    if player_number is None:
        writer.close()
        await writer.wait_closed()
        return
    
    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break
            
            message = json.loads(data.decode('utf-8'))
            command = message.get("command", "").strip()
            logging.info(f"Received command from {address}: {command}")
            
            if command == 'status':
                status_message = {
                    "broadcast": [
                        f"Player {i} is {'ready' if ready else 'not ready'}"
                        for i, ready in enumerate(game_state.ready_status)
                    ]
                }
                message = json.dumps(status_message) + "\n"
                writer.write(message.encode('utf-8'))
                await writer.drain()
                
            elif command == 'ready':
                await game_state.set_ready(writer, address)
            elif command == 'exit':
                break
            else:
                error_message = {"error": f"Unknown command received: {command}"}
                message = json.dumps(error_message) + "\n"
                writer.write(message.encode('utf-8'))
                await writer.drain()    
    except Exception as e:
        logging.error(f"Error handling client {address}: {e}")
        print(f"Error handling client {address}: {e}")
    finally:
        await game_state.remove_client(writer, address)
        writer.close()
        await writer.wait_closed()

async def main():
    parser = argparse.ArgumentParser(description="TCPoker Server")
    parser.add_argument('-i', '--ip', type=str, required=True, help='Host IP Address.')
    parser.add_argument('-p', '--port', type=int, required=True, help='Port to listen on.')
    parser.add_argument('-c', '--connections', type=int, required=True, help='Number of players to start the game.')
    args = parser.parse_args()
    
    setup_logging()
    game_state = GameState(args.connections)
    
    # Starts an asynchronous server using asyncio. Per the documentation, this server is a TCP server with setblocking(False) 
    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, game_state),
        args.ip, args.port)
    
    addr = (args.ip, args.port)
    logging.info(f"Server listening on {addr}")
    print(f"Server listening on {addr}")
    
    async with server:
        try:
            await server.serve_forever()
        except KeyboardInterrupt:
            logging.info("Server shutdown initiated by KeyboardInterrupt.")
           
            
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server terminated by user.")