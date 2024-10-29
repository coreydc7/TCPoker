import asyncio
import argparse
import logging

def setup_logging():
    logging.basicConfig(
        filename='server.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

class GameState:
    def __init__(self, num_players):
        self.connected_clients = []
        self.num_players = num_players
        self.ready_status = [False] * num_players
        self.lock = asyncio.Lock()
        
    async def add_client(self, writer, address):
        async with self.lock:
            if len(self.connected_clients) < self.num_players:
                self.connected_clients.append((writer, address))
                self.ready_status[len(self.connected_clients)-1] = False
                await self.broadcast(f"{address} has joined the game.")
                logging.info(f"{address} joined the game.")
                return len(self.connected_clients)
            else:
                writer.write("Unable to join: table is full.".encode('utf-8'))
                await writer.drain()
                logging.info(f"{address} attempted to join but the table is full.")
                return None
                
    async def remove_client(self, writer, address):
        async with self.lock:
            for i, (w, addr) in enumerate(self.connected_clients):
                if w == writer:
                    del self.connected_clients[i]
                    del self.ready_status[i]
                    await self.broadcast(f"{address} has left the game.")
                    logging.info(f"{address} disconnected.")
                    break
                    
    async def broadcast(self, message):
        for writer, addr in self.connected_clients:
            try:
                writer.write(f"Server: {message}".encode('utf-8'))
                await writer.drain()
            except Exception as e:
                print(f"Failed to send message to {addr}: {e}")
                logging.error(f"Failed to send message to {addr}: {e}")
                
    async def set_ready(self, writer, address):
        async with self.lock:
            for i, (w, addr) in enumerate(self.connected_clients):
                if w == writer:
                    self.ready_status[i] = True
                    await self.broadcast(f"{address} is ready.")
                    logging.info(f"{address} is ready.")
                    if all(self.ready_status):
                        await self.broadcast("All players are ready. Starting Texas Hold'em!")
                        logging.info("All players are ready. Starting game.")
                    break

async def handle_client(reader, writer, game_state):
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
            command = data.decode('utf-8').strip()
            logging.info(f"Received command from {address}: {command}")
            if command == 'status':
                status = "\n".join([
                    f"Player {i+1} is {'ready' if ready else 'not ready'}"
                    for i, ready in enumerate(game_state.ready_status)
                ])
                writer.write(status.encode('utf-8'))
                await writer.drain()
            elif command == 'ready':
                await game_state.set_ready(writer, address)
            elif command == 'exit':
                break
            else:
                writer.write(f"Unknown command received: {command}".encode('utf-8'))
                await writer.drain()
                    
    except Exception as e:
        logging.error(f"Error handling client {address}: {e}")
    finally:
        await game_state.remove_client(writer, address)
        writer.close()
        await writer.wait_closed()

async def main():
    parser = argparse.ArgumentParser(description="TCPoker Server")
    parser.add_argument('-i', '--ip', type=str, required=True, help='Host IP Address.')
    parser.add_argument('-p', '--port', type=int, required=True, help='Port to listen on.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable debug logging.')
    parser.add_argument('-c', '--connections', type=int, required=True, help='Number of players to start the game.')
    args = parser.parse_args()
    
    setup_logging()
    game_state = GameState(args.connections)
    
    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, game_state),
        args.ip, args.port)
    
    addr = server.sockets[0].getsockname()
    logging.info(f"Server listening on {addr}")
    print(f"Server listening on {addr}")
    
    async with server:
        try:
            await server.serve_forever()
        except KeyboardInterrupt:
            print("Server shutting down.")
            logging.info("Server shutdown initiated by KeyboardInterrupt.")
            
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server terminated by user.")