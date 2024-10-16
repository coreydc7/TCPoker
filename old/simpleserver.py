import asyncio
import json

class GameState:
    def __init__(self, num_players):
        self.connected_clients = []
        self.num_players = num_players
    
    async def broadcast(self, message):
        for client in self.connected_clients:
            await self.send_message(client, message)
    
    async def send_message(self, client, message):
        try:
            client.write(json.dumps(message).encode('utf-8'))
            await client.drain()
        except Exception as e:
            print(f"Error sending message to {client.get_extra_info('peername')}: {e}")

    def add_client(self, client):
        self.connected_clients.append(client)
        asyncio.create_task(self.broadcast({"result": "A new player has joined the game."}))
    
    def remove_client(self, client):
        self.connected_clients.remove(client)
        asyncio.create_task(self.broadcast({"result": "A player has left the game."}))

async def handle_client(reader, writer, game_state):
    addr = writer.get_extra_info('peername')
    print(f"Accepted connection from {addr}")
    game_state.add_client(writer)
    
    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break
            message = json.loads(data.decode('utf-8'))
            action = message.get("action")
            # Handle the message (e.g., join, status, ready, exit)
            if action == 'exit':
                await game_state.broadcast({"result": f"Player {addr} has exited."})
                break
    except Exception as e:
        print(f"Error with client {addr}: {e}")
    finally:
        game_state.remove_client(writer)
        writer.close()
        await writer.wait_closed()

async def main(host, port, num_clients):
    game_state = GameState(num_clients)
    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, game_state),
        host, port
    )
    async with server:
        print(f"Listening on {host}:{port}")
        await server.serve_forever()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="TCPoker Server")
    parser.add_argument('-i', '--ip', type=str, required=True, help='Host IP')
    parser.add_argument('-p', '--port', type=int, required=True, help='Port')
    parser.add_argument('-c', '--connections', type=int, required=True, help='Number of clients required to start game.')
    args = parser.parse_args()
    
    asyncio.run(main(args.ip, args.port, args.connections))