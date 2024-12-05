import asyncio
import json
import logging
import argparse
import random
from itertools import combinations
from collections import Counter

logging.basicConfig(
    # Configure logging
    filename='server.log',
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
    )



class Player:
    ''' Manages state of each player '''
    def __init__(self, name, writer, stack=100):
        self.name = name
        self.writer = writer
        self.ready = False
        self.stack = stack  
        self.hand = []
        self.ante_placed = False
        self.hand_placed = False
        self.last_action = None
        self.folded = False
        self.total_bet = 0



class TCPokerServer:
    ''' Manages state of the Poker Game '''
    def __init__(self, seed=None):
        self.game_active = False
        self.players = []
        self.pot = 0
        self.ante = 10
        self.random = random.Random(seed)
        self.deck = self.create_deck()
        self.community_cards = []
        self.game_task = None
        self.current_player = None
        self.dealer_position = 0    # Who goes first during betting rounds
        self.current_bet = 0
        self.pot_committed = {}     # How much each player has bet during each round
        self.round_complete = False
        self.last_bettor = None
        self.best_hands = {}
        self.ante_event = asyncio.Event()   # Signals when all antes are collected
        self.current_player_event = asyncio.Event()     # Signals when current players turn is over
        self.betting_round_event = asyncio.Event()  # Signals when the betting round is complete
        self.best_hands_event = asyncio.Event()     # Signals when both players have sent in their best hands
        self.solver = False     # Enables automatic hand solver

    def cleanup(self):
        ''' Cleans up server state if a game in-progress is cancelled '''
        logging.info("Cleaning up game state...")
        self.game_active = False
        for player in self.players:
            player.hand = []
            player.ante_placed = False
            player.hand_placed = False
            player.last_action = None
            player.folded = False
            player.total_bet = 0
        if self.game_task:
            self.game_task.cancel()
            self.game_task = None
        self.pot = 0
        self.deck = self.create_deck()
        self.community_cards = []
        self.current_player = None
        self.current_bet = 0
        self.pot_committed = {}
        self.round_complete = False
        self.last_bettor = None
        self.best_hands = {}
        self.ante_event.clear()
        self.current_player_event.clear()
        self.betting_round_event.clear()
        self.best_hands_event.clear()

    def check_all_ante(self):
        if all(player.ante_placed for player in self.players):
            self.ante_event.set()
        else:
            self.ante_event.clear()

    def check_all_hands(self):
        if all(player.hand_placed for player in self.players):
            self.best_hands_event.set()
        else:
            self.best_hands_event.clear()


    def create_deck(self):
        ''' Create and shuffle a deck '''
        suits = ['♠', '♥', '♦', '♣']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
        deck = [f"{rank}{suit}" for suit in suits for rank in ranks]
        self.random.shuffle(deck)
        return deck


    async def handle_client(self, reader, writer):
        ''' Main client event handler. Each time a client connects, this couroutine is started '''
        addr = writer.get_extra_info('peername')
        print(f"Accepted new connection from {addr}")
        logging.info(f"Accepted new connection from {addr}")

        # First thing clients do is join by sending their custom username, receive it here
        try:
            data = await reader.readline()      # Respects the '\n' delimiter used by client.py
            message = json.loads(data.decode())
            if "username" not in message:       # Verify first message received from client is "username"
                raise ValueError("Client username not found.")
            player = Player(message["username"], writer)        # Create new Player for connected client
            self.players.append(player)
            logging.info(f"{addr} has chosen the username: {player.name}")
            await self.broadcast({"broadcast": f"{player.name} has joined the game."})      

            # After client has joined the game, sit and wait for client to send commands
            while True:
                data = await reader.readline()
                if not data:
                    break
                message = json.loads(data.decode())
                logging.info(f"Received message from {player.name}: {message}")
                await self.process_message(player, message)     # Process any received messages
        except json.JSONDecodeError:
            logging.error("Invalid JSON received from client.")
        except Exception as e:
            logging.error(f"Error when handling client: {e}")
        finally:
            # Cleanup after 'exit' command or unexpected client disconnect
            print(f"Connection closed for {addr}")
            logging.info(f"Connection closed for {addr}")
            self.players.remove(player)
            await self.broadcast({"broadcast": f"{player.name} has left the game."})
            # When a client disconnects while a game is in progress, cancel the game and return the other client to lobby. 
            # TODO: implement saving of player state, so players who disconnect can rejoin using their username
            if(self.game_active):   
                print("Ending current game...")
                await self.broadcast({"broadcast": "Ending current game..."})
                await self.broadcast({"game_state": "lobby"})
                # Refund any bets made by the still-connected client
                for client in self.players:
                    if client != player:
                        client.stack += client.total_bet
                self.cleanup()
    
            writer.close()
            await writer.wait_closed()


    async def process_message(self, player, message):
        ''' Processes any commands received after username stage. The list of commands a client is allowed to send is managed by the client'''
        if "command" in message:
            command = message["command"][0]

            if command == "ready":
                if player.ready:
                    await self.send_message(player, {"broadcast": "You are already ready, use 'status' to view everyones ready status."})
                    return
                
                player.ready = True
                await self.broadcast({"broadcast": f"{player.name} is ready."})
                logging.info(f"{player.name} is ready.")
                await self.check_all_ready()        # After a player readies up, check if all clients are ready
            
            elif command == "status":
                status = {p.name: p.ready for p in self.players}
                await self.send_message(player, {"status": status})
            
            elif command == "exit":
                return
            
            elif command.startswith("ante"):    # Usage: ante <amount>
                amount = int(message["command"][1]) if len(message["command"]) > 1 else 0
                
                if amount <= player.stack:
                    self.pot += amount
                    player.stack -= amount
                    player.total_bet += amount
                    await self.broadcast({"broadcast": f"{player.name} bets ${amount}. Pot is now ${self.pot}."})
                    logging.info(f"{player.name} bets ${amount}. Pot: ${self.pot}")
                    await self.send_message(player, {"action": "clear_prompt"})
                    
                    if not player.ante_placed:
                        player.ante_placed = True
                        self.check_all_ante()
                        
                        if not self.ante_event.is_set():
                            await self.send_message(player, {"broadcast": "Waiting for all players to place their ante..."})
                
                else:
                    await self.send_message(player, {"error": "Bet amount exceeds stack."})
            
            elif command in ['check', 'bet', 'call', 'raise', 'fold']:
                if player == self.current_player:
                    amount = int(message["command"][1]) if len(message["command"]) > 1 else 0
                    
                    if await self.handle_betting_action(player, command, amount):
                        self.current_player_event.set()     # Set event to Move to next players turn
                
                else:
                    await self.send_message(player, {"error": "Please wait your turn"})
            
            elif command == "hand":
                poker_hand = self.parse_hand(player, message["command"])
                self.best_hands[player] = poker_hand
                player.hand_placed = True
                await self.send_message(player, {"action":"clear_prompt"})
                self.check_all_hands()  # Check if all best hands are in

            else:
                await self.send_message(player, {"error": "Unknown command."})
        
        else:
            await self.send_message(player, {"error": "Invalid message format."})


    async def check_all_ready(self):
        ''' Check if all clients are ready to start the game '''
        if len(self.players) == 2 and all(p.ready for p in self.players):
            self.game_active = True
            await self.broadcast({"start_game": True})      # Notify clients that game has started
            self.game_task = asyncio.create_task(self.start_game())


    async def start_game(self):
        ''' Main Poker game flow'''
        await self.broadcast({"broadcast": "All players are ready. Starting the game!"})
        # 1. Collect the ante from both clients. Clients must post the ante to buy into the hand. 
        for player in self.players:
            await self.send_message(player, {"stack": player.stack})
        await self.broadcast({"action": "collect_ante", "amount": self.ante})
        # 2. Wait for the antes to be collected
        await self.ante_event.wait() 
        # 3. Deal hole cards, and show them to the client (pre-flop)
        await self.deal_hands()
        # 4. Begin the first betting round 
        await self.show_hands()
        await self.broadcast({"broadcast": "Beginning first betting round..."})
        await self.betting_round()
        # 5. Wait for the first betting round to complete
        await self.betting_round_event.wait()
        # 6. Deal three community cards (Flop)
        await self.broadcast({"broadcast": "Dealing community cards..."})
        await self.deal_community_cards(3)
        # 7. Begin the second betting round
        await self.show_hands()
        await self.broadcast({"broadcast": "Beginning second betting round..."})
        await self.betting_round()
        # 8. Wait for the second betting round to complete
        await self.betting_round_event.wait()
        # 9. Deal one community card (Turn)
        await self.deal_community_cards(1)
        # 10. Begin the third betting round
        await self.show_hands()
        await self.broadcast({"broadcast": "Beginning third betting round..."})
        await self.betting_round()
        # 11. Wait for the third betting round to complete
        await self.betting_round_event.wait()
        # 12. Deal final community card (River)
        await self.deal_community_cards(1)
        # 13. Begin the final betting round
        await self.show_hands()
        await self.broadcast({"broadcast": "Beginning final betting round..."})
        await self.betting_round()
        # 14. Wait for the final betting round to complete
        await self.betting_round_event.wait()
        # 15. Skip over comparing hands if all but one player has folded
        active_players = [p for p in self.players if not p.folded]
        if len(active_players) > 1:
        # 16. If automatic solver is set, best hands will be determined automatically. Else clients must submit their own best hands
            if self.solver:
                for player in self.players:
                    best_hand = self.get_best_hand(player.hand + self.community_cards)
                    self.best_hands[player] = best_hand
                self.best_hands_event.set() 
            else:
                await self.broadcast({"action": "collect_hands"})
        # 17. Wait for best hands to be received 
            await self.best_hands_event.wait()
        # 18. Determine who wins the pot based on who has the best poker hand
        await self.determine_winner()


    async def deal_hands(self):
        ''' Deals hole cards to each player '''
        for player in self.players:
            player.hand = [self.deck.pop(), self.deck.pop()]
            logging.info(f"Dealt to {player.name}: {player.hand}")

    async def show_hands(self):
        ''' Sends each players hand and stack as a message for the client to display '''
        for player in self.players:
            await self.send_message(player, {"hand": player.hand})
            await self.send_message(player, {"stack": player.stack})
            

    async def betting_round(self):
        ''' Manages betting round '''
        self.current_bet = 0
        self.pot_committed = {player: 0 for player in self.players}
        self.round_complete = False
        self.betting_round_event.clear()
        for p in self.players:
            p.last_action = None
        self.last_bettor = None

        while not self.round_complete:
            for i in range(2):
                if self.round_complete:
                    break
                await self.handle_player_turn(self.players[(i + self.dealer_position) % 2])   # Alternates between players each round


    async def handle_player_turn(self, player):
        ''' Handle individual player's turn '''
        if player.folded:
            return
        
        # Check if round should end before each turn
        if self.should_end_round(player):
            await self.broadcast({"broadcast": f"Betting round complete. Pot is ${self.pot}"})
            self.round_complete = True
            self.betting_round_event.set()
            return
        
        self.current_player = player
        self.current_player_event.clear()

        # Determine valid actions
        valid_actions = self.get_valid_actions(player)

        # Send turn message to player
        await self.send_message(player, {
            "action": "collect_bets",
            "valid_actions": valid_actions,
            "current_bet": self.current_bet,
            "to_call": self.current_bet - self.pot_committed[player],
            "pot": self.pot
        })

        # Send waiting for turn message to other player
        for client in self.players:
            if client != player:
                await self.send_message(client, {"broadcast":f"It is currently {player.name}'s turn. Please wait your turn."})

        # Wait for client action
        await self.current_player_event.wait()

    
    def should_end_round(self, current_player):
        ''' Determine if betting round should end 
            A round should end if:
            1. All players but one have folded
            2. All players check, no one bets
            3. If betting action occurs, all active players must bet and their bet amounts must be equal.
        '''
        active_players = [p for p in self.players if not p.folded]

        # End round if all players but one have folded
        if len(active_players) == 1:
            return True
        
        # End round if no bets have been made and all players have checked
        if self.current_bet == 0 and all(p.last_action == 'check' for p in active_players):
            return True

        # If there's been betting action
        if self.last_bettor:
            # Check we've gone back to the last bettor and all players have matched
            is_last_bettor = current_player == self.last_bettor
            all_bets_matched = all(self.pot_committed[p] == self.current_bet for p in active_players)
            return is_last_bettor and all_bets_matched

        return False
    
    
    async def deal_community_cards(self, num_cards):
        ''' Pop num_cards cards from the deck and add to community cards
            Display community cards to the clients '''
        for _ in range(num_cards):
            self.community_cards.append(self.deck.pop())
        await self.broadcast({"community_cards": self.community_cards})
        logging.info(f"Dealt community cards: {self.community_cards}")
    
    def get_valid_actions(self, player):
        ''' Determine valid actions for player '''
        if player.folded:
            return []
        
        to_call = self.current_bet - self.pot_committed[player]

        if self.current_bet == 0:
            return ['check', 'bet']
        elif to_call > player.stack:
                return ['fold']
        elif player.stack >= to_call * 2: # must have enough to raise
            return ['call', 'raise', 'fold']
        else:
            return ['call', 'fold']
            

    async def handle_betting_action(self, player, action, amount):
        ''' Handle betting round actions '''
        if action == 'check' and self.current_bet == 0:
            player.last_action = 'check'
            await self.broadcast({"broadcast": f"{player.name} has checked. Pot: ${self.pot}"})
            logging.info(f"{player.name} has checked. Pot: ${self.pot}")
            await self.send_message(player, {"action":"clear_prompt"})
            return True
        elif action == 'bet' and self.current_bet == 0:
            if amount >= self.ante and amount <= player.stack:
                self.current_bet = amount
                self.pot += amount
                self.pot_committed[player] = amount
                player.stack -= amount
                player.total_bet += amount
                player.last_action = 'bet'
                self.last_bettor = player
                await self.broadcast({"broadcast": f"{player.name} has bet ${amount}. Pot: ${self.pot}"})
                logging.info(f"{player.name} has bet ${amount}. Pot: ${self.pot}")
                await self.send_message(player, {"action":"clear_prompt"})
                return True
            else:
                await self.send_message(player, {"broadcast":"Invalid bet. Make sure you have enough money to bet."})
        elif action == 'call' and self.current_bet > 0:
            to_call = self.current_bet - self.pot_committed[player]
            if to_call <= player.stack:
                self.pot += to_call
                self.pot_committed[player] = self.current_bet
                player.stack -= to_call
                player.total_bet += to_call
                player.last_action = 'call'
                await self.broadcast({"broadcast": f"{player.name} has called ${to_call}. Pot: ${self.pot}"})
                logging.info(f"{player.name} has called ${to_call}. Pot: ${self.pot}")
                await self.send_message(player, {"action":"clear_prompt"})
                return True
            else:
                await self.send_message(player, {"broadcast":"Invalid call. Make sure you have enough money to call the current bet."})
        elif action == 'raise':
            if amount >= self.current_bet * 2 and amount <= player.stack:
                to_add = amount - self.pot_committed[player]
                self.pot += to_add
                self.current_bet = amount
                self.pot_committed[player] = amount
                player.stack -= to_add
                player.total_bet += to_add
                player.last_action = 'raise'
                self.last_bettor = player
                await self.broadcast({"broadcast": f"{player.name} has raised to ${to_add}. Pot: ${self.pot}"})
                logging.info(f"{player.name} has raised to ${to_add}. Pot: ${self.pot}")
                await self.send_message(player, {"action":"clear_prompt"})
                return True
            else:
                await self.send_message(player, {"broadcast":"Invalid raise. You must raise by atleast 2x the current bet. Make sure you have enough money to raise the bet."})
        elif action == 'fold':
            player.folded = True
            player.last_action = 'fold'
            await self.send_message(player, {"action":"clear_prompt"})
            return True
        
        return False
    
    def parse_hand(self, player, hand):
        ''' Parses the hand command containing a clients best poker hand'''
        cards = hand[1:]
        selected_cards = []

        for card in cards:
            card_type = card[0]
            pos = int(card[1]) - 1

            if card_type == 'c':
                selected_cards.append(self.community_cards[pos])
            else:
                selected_cards.append(player.hand[pos])

        return selected_cards

    async def broadcast(self, message):
        ''' Send a message to all players '''
        for player in self.players:
            await self.send_message(player, message)


    async def send_message(self, player, message):
        ''' Send a message to a specific player '''
        try:
            player.writer.write((json.dumps(message) + "\n").encode())      # All messages end with '\n' delimiter
            await player.writer.drain()
            logging.info(f"Sent to {player.name}: {message}")
        except Exception as e:
            logging.error(f"Failed to send message to {player.name}: {e}")

    
    async def determine_winner(self):
        ''' Once the all players have submitted their best 5-card poker hands in self.best_hands, 
            Evaluate the winner of the pot and send results. Cleanup state and move onto the next round'''
        active_players = [p for p in self.players if not p.folded]

        # Game is won if all players but one have folded
        if len(active_players) == 1:
            winner_player = active_players[0]
            logging.info(f"{winner_player.name} has won the ${self.pot} pot as all other players have folded.")
            await self.broadcast({"broadcast":f"{winner_player.name} has won the ${self.pot} pot as all other players have folded."})
            winner_player.stack += self.pot
            await self.send_message(winner_player, {"broadcast":f"Congratulations on winning! You won ${self.pot}. You now have ${winner_player.stack} in your stack."})
        else:
            evaluated_hands = {}

            for player in self.players:
                logging.info(f"Evaluating {player.name}'s hand: {self.best_hands[player]}")
                evaluated_hands[player] = self.evaluate_hand(self.best_hands[player])

            # Sort players by their evaluated hand ranking and relevant cards for breaking ties
            sorted_players = sorted(evaluated_hands.items(), key=lambda x: x[1], reverse=True)

            # First player in list is the winner
            winner_player, winner_hand_info = sorted_players[0]
            loser_player, loser_hand_info = sorted_players[1]

            # Determine the name of the winning hand based on its ranking.
            hand_rankings = [
                "High Card", "One Pair", "Two Pair", "Three of a Kind", 
                "Straight", "Flush", "Full House", "Four of a Kind", 
                "Straight Flush", "Royal Flush"
            ]

            winning_hand_name = hand_rankings[winner_hand_info[0]]
            losing_hand_name = hand_rankings[loser_hand_info[0]]

            # Check for an exact tie
            if winner_hand_info == loser_hand_info:     # Same hand name and tie breaking cards
                await self.broadcast({"broadcast": f"How rare! An exact tie! {winner_player.name} and {loser_player.name} split the pot of ${self.pot} with a {winning_hand_name}."})
                await self.broadcast({"broadcast": f"{winner_player.name} had a {self.best_hands[winner_player]}, and {loser_player.name} had a {self.best_hands[loser_player]}."})
                logging.info(f"The game ended in an exact tie. Both players had a {winning_hand_name}. ")
                winner_player.stack += self.pot/2
                loser_player.stack += self.pot/2
                await self.send_message(winner_player, {"broadcast":f"Congratulations on winning! You won ${self.pot/2}. You now have ${winner_player.stack} in your stack."})
                await self.send_message(loser_player, {"broadcast":f"Congratulations on winning! You won ${self.pot/2}. You now have ${loser_player.stack} in your stack."})

            else:
                # Broadcast the winner 
                await self.broadcast({"broadcast": f"{winner_player.name} has won ${self.pot} with a {winning_hand_name}!"})
                await self.broadcast({"broadcast": f"{winner_player.name} has won the game with the hand: {winning_hand_name} - {self.best_hands[winner_player]}, beating {loser_player.name}'s hand: {losing_hand_name} - {self.best_hands[loser_player]}."})
                logging.info(f"{winner_player.name} has won the game with the hand: {winning_hand_name} - {self.best_hands[winner_player]}, beating {loser_player.name}'s hand: {losing_hand_name} - {self.best_hands[loser_player]}.")
                winner_player.stack += self.pot
                await self.send_message(winner_player, {"broadcast":f"Congratulations on winning! You won ${self.pot}. You now have ${winner_player.stack} in your stack."})

        await self.broadcast({"broadcast": "Ending current round, ready up to play another!"})
        await self.broadcast({"game_state": "lobby"})
        self.dealer_position += 1
        for player in self.players:
            player.ready = False
        self.cleanup()


    def evaluate_hand(self, hand):
        ''' Evaluates a hand and returns its rank and relevant cards for tie-breaking '''
        # Extract ranks and suits from hand
        card_ranks = {str(n): n for n in range (2, 10)}
        card_ranks.update({'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14})
        ranks = sorted([card_ranks[card[:-1]] for card in hand], reverse=True)
        suits = [card[-1] for card in hand]
        
        # Check for a flush 
        is_flush = len(set(suits)) == 1

        # Check for a straight
        is_straight = ranks == list(range(ranks[0], ranks[0] - 5, -1))

        # Check for an ace-low straight
        if ranks == [14, 5, 4, 3, 2]:
            is_straight = True
            ranks = [5, 4, 3, 2, 1]

        # Count occurrences of each rank
        rank_counts = Counter(ranks).most_common()

        # Determine hand type based on rank counts and other checks
        if is_flush and is_straight:
            return (9 if ranks[0] == 14 else 8, ranks)  # Royal flush or Straight flush
        
        elif rank_counts[0][1] == 4:
            return (7, [rank_counts[0][0], rank_counts[1][0]])  # Four of a kind
        
        elif rank_counts[0][1] == 3 and rank_counts[1][1] == 2:
            return (6, [rank_counts[0][0], rank_counts[1][0]])  # Full house
        
        elif is_flush:
            return (5, ranks)   # Flush
        
        elif is_straight:
            return (4, ranks)   # Straight
        
        elif rank_counts[0][1] == 3:
            return (3, [rank_counts[0][0]] + sorted([rank for rank, count in rank_counts if count == 1], reverse=True))     # Three of a kind
        
        elif rank_counts[0][1] == 2 and rank_counts[1][1] == 2:
            return (2, sorted([rank_counts[0][0], rank_counts[1][0]], reverse=True) + [rank_counts[2][0]])  # Two pair
        
        elif rank_counts[0][1] == 2:
            return (1, [rank_counts[0][0]] + sorted([rank for rank, count in rank_counts if count == 1], reverse=True))     # One pair
        
        else: 
            return (0, ranks)   # High card
        

    def get_best_hand(self, cards):
        ''' Algorithmically determines the best 5-card poker hand from players 2 hand cards + 5 community cards '''
        best_score = (-1, [])
        best_hand = []

        for hand in combinations(cards, 5):
            score = self.evaluate_hand(hand)
            if score > best_score:
                best_score = score
                best_hand = hand
        return best_hand


async def main():
    parser = argparse.ArgumentParser(description="TCPoker Server")
    parser.add_argument('-p', '--port', type=int, required=True, help='Port to listen on.')
    parser.add_argument('-s', '--solve', action='store_true', required=False, help='Enable automatic hand solver.')
    args = parser.parse_args() 
    
    poker_server = TCPokerServer()
    poker_server.solver = args.solve
    
    # Start TCP server
    server = await asyncio.start_server(poker_server.handle_client, '0.0.0.0', args.port)
    addr = ('0.0.0.0', args.port)
    logging.info(f"Server listening on {addr}")
    print(f"Server listening on {addr}")
    
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server terminated by user.")
        logging.info("Server terminated by user.")