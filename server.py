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
        self.ready_status = [(False, '') for _ in range(num_players)]
        self.lock = asyncio.Lock()
        self.game = TexasHoldEm(num_players, self)
        self.game_active = False
        self.events = {}
        
    async def add_client(self, writer, address, username):
        ''' Handles adding a client to list of connected clients '''
        async with self.lock:
            if len(self.connected_clients) < self.num_players:
                self.connected_clients.append((writer, address, username))
                self.ready_status[len(self.connected_clients) - 1] = (False, username)
                print(f"{address} has connected to the game as {username}.")
                await self.broadcast("broadcast", f"{address} has joined the game as {username}.")
                logging.info(f"{address} joined the game with the username {username}.")
                return len(self.connected_clients)
            else:
                message = json.dumps({"error": "Unable to join: table is full."}) + '\n'
                writer.write(message.encode('utf-8'))
                await writer.drain()
                logging.info(f"{address} attempted to join but the table was full.")
                return None
                
    async def remove_client(self, writer):
        ''' Removes a client from the list of connected clients '''
        async with self.lock:
            for i, (w, addr, username) in enumerate(self.connected_clients[:]):
                if w == writer:
                    self.connected_clients.pop(i)
                    self.ready_status.pop(i)
                    print(f"{username} has disconnected.")
                    await self.broadcast("broadcast", f"{username} has left the game.")
                    logging.info(f"{username} ({addr}) disconnected.")
                    break
            if(self.game_active and len(self.connected_clients) == 0):
                print("All players have left, stopping game.")
                logging.info("All players have left, stopping game.")
                self.game_active = False
                self.game.reset_game()
                
    async def broadcast(self, key, value):
        ''' Writes a JSON message to all connected clients, using {key:message} '''
        for writer, addr, username in self.connected_clients:
            try:
                message = json.dumps({key: value}) + "\n"   # New-line delimiter
                writer.write(message.encode('utf-8'))
                await writer.drain()
            except Exception as e:
                print(f"Failed to send message to {username} ({addr}): {e}")
                logging.error(f"Failed to send message to {username} ({addr}): {e}")
    
    async def broadcast_others(self, key, value, player):
        ''' Writes a JSON message to all other connected clients, besides player, using {key:message} '''
        for writer, addr, username in self.connected_clients:
            try:
                if writer != player:
                    message = json.dumps({key: value}) + "\n"
                    writer.write(message.encode('utf-8'))
                    await writer.drain()
            except Exception as e:
                print(f"Failed to send message to {username} ({addr}): {e}")
                logging.error(f"Failed to send message to {username} ({addr}): {e}")

    async def broadcast_client(self, current_player, key, value):
        ''' Sends a JSON message to current_player using key:value '''
        writer, addr, username = self.connected_clients[current_player]
        try:
            message = json.dumps({key: value}) + "\n"
            writer.write(message.encode('utf-8'))
            await writer.drain()
            logging.info(f"Sent {message} to {username} ({addr}).")
        except Exception as e:
            logging.error(f"Failed to send {message} to {username} ({addr}): {e}")

    async def set_ready(self, writer):
        ''' Marks a client as ready, checks for readiness to start game '''
        async with self.lock:
            for i, (w, addr, username) in enumerate(self.connected_clients):
                if w == writer:
                    self.ready_status[i] = (True, username)
                    await self.broadcast("broadcast", f"{username} is ready.")
                    logging.info(f"{username} ({addr}) is ready.")
                    
                    # Start game if all players are ready
                    all_ready = True
                    for (ready, username) in self.ready_status:
                        if(ready == False):
                            all_ready = False
                    if all_ready:
                        await self.start_game()
                    break
    
    async def start_game(self):
        await self.broadcast("game_start", "All players are ready. Starting Texas Hold'em!")
        await asyncio.sleep(0.1)      # Always add a small delay in-between messages for proper sequencing
        logging.info("All players are ready. Starting game.")
        self.game_active = True
        
        await self.game.play_hand()   # Starts the main game flow
    
    
async def handle_client(reader, writer, game_state):
    ''' Main client event handler '''
    address = writer.get_extra_info('peername')
    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break
            
            message = json.loads(data.decode('utf-8'))
            logging.info(f"Received message from {address}: {message}")

            # Messages are JSON key:value pairs
            message_key = list(message.keys())[0]
            if message_key == 'username':     # The first thing a client does upon connection is send their custom username as a message
                added_player = await game_state.add_client(writer, address, message['username'])
                
                if added_player is None:
                    writer.close()
                    await writer.wait_closed()
                    return
                        
            elif message_key == 'command':
                command = message.get("command", "")
                # Handle the various game commands
                if command[0] == 'status':
                    status_message = {
                        "status": [
                            f"{player[1]} is {'ready' if player[0] else 'not ready'}"
                            for player in game_state.ready_status
                        ]
                    }
                    message = json.dumps(status_message) + "\n"
                    writer.write(message.encode('utf-8'))
                    await writer.drain()
                    
                elif command[0] == 'ready':
                    await game_state.set_ready(writer)
                elif command[0] == 'exit':
                    break
                elif command[0] == 'bet':
                    if(len(command) != 2):
                        error_message = {"error": f"Please enter a bet amount (ex: bet 10)"}
                        message = json.dumps(error_message) + "\n"
                        writer.write(message.encode('utf-8'))
                        await writer.drain()   
                    else:
                        # Find the username and index of player who sent the command
                        _username = None
                        _index = None
                        for i, players in enumerate(game_state.connected_clients):
                            if players[0] == writer:
                                _username = players[2]
                                _index = i
                                break
                        try:
                            bet_amount = int(command[1])
                            game_state.game.players[_index].bet(bet_amount)
                            game_state.game.pot += bet_amount
                            if not game_state.events['small_blind'].is_set():
                                game_state.events['small_blind'].set()
                            await game_state.broadcast("broadcast", f"{_username} has added ${bet_amount} to the pot.")
                            logging.info(f"{_username} ({address}) bets ${bet_amount}")
                        except ValueError:
                            error_message = {"error": f"Please enter a valid bet amount. You currently have {game_state.game.players[_index].stack}"}
                            message = json.dumps(error_message) + "\n"
                            writer.write(message.encode('utf-8'))
                            await writer.drain()    
                else:
                    error_message = {"error": f"Unknown command received: {command[0]}"}
                    message = json.dumps(error_message) + "\n"
                    writer.write(message.encode('utf-8'))
                    await writer.drain()    
    except Exception as e:
        logging.error(f"Error handling client {address}: {e}")
        print(f"Error handling client {address}: {e}")
    finally:
        try:
            await game_state.remove_client(writer)
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            logging.error(f"Error during handle_client cleanup: {e}")
            pass

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