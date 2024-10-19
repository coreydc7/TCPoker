import random
from enum import Enum, IntEnum
from dataclasses import dataclass, field
from typing import List, Tuple
from collections import Counter
from itertools import combinations
from functools import total_ordering


class Suit(Enum):
    SPADES = "♠"
    HEARTS = "♥"
    DIAMONDS = "♦"
    CLUBS = "♣"
    
class Rank(IntEnum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    J = 11
    Q = 12
    K = 13
    A = 14
    
class HandRank(IntEnum):
    HIGH_CARD = 1
    PAIR = 2
    TWO_PAIR = 3
    THREE_OF_A_KIND = 4
    STRAIGHT = 5
    FLUSH = 6
    FULL_HOUSE = 7
    FOUR_OF_A_KIND = 8
    STRAIGHT_FLUSH = 9
    ROYAL_FLUSH = 10
    
    
@total_ordering # This automatically generates the remaining comparison methods based on __eq__ and __lt__
@dataclass
class Card:
    suit: Suit
    rank: Rank

    def __str__(self) -> str:
        return f"{self.rank.value}{self.suit.value}"
    
    # Comparisons operators
    def __eq__(self, other):
        if not isinstance(other, Card):
            return NotImplemented
        return (self.rank) == (other.rank)
    
    def __lt__(self, other):
        if not isinstance(other, Card):
            return NotImplemented
        return (self.rank.value) < (other.rank.value)
   
@dataclass 
class Player:
    stack: int
    hand: List[Card] = field(default_factory=list)
    
    def add_card(self, card: Card):
        self.hand.append(card)
        
    def clear_cards(self):
        self.hand.clear()
        
    def bet(self, amount: int):
        if amount > self.stack:
            raise ValueError("Not enough chips to bet")
        self.stack -= amount
        return amount
    
    def win(self, amount: int):
        self.stack += amount
        
    def __str__(self) -> str:
        return f"Stack: ${self.stack}, hand: {', '.join(str(card) for card in self.hand)}"
        
    

'''The entire gamestate is stored using this class '''
class TexasHoldEm:
    def __init__(self, num_players, starting_stack=100, seed=None):
        self.num_players = num_players
        self.random = random.Random(seed)
        self.deck = self.create_deck()
        self.community_cards = []
        self.players = [Player(starting_stack) for _ in range(num_players)]
        self.pot = 0
        self.dealer_position = 0
        self.small_blind = 0
        self.big_blind = 0
        self.players_ready = [False] * num_players
        
    def set_player_ready(self, player_idx):
        self.players_ready[player_idx] = True
        
    def all_players_ready(self):
        return all(self.players_ready)
    
    def reset_player_readiness(self):
        self.players_ready = [False] * self.num_players
        
    def create_deck(self) -> List[Card]:
        ''' Create and shuffle a standard 52-card deck '''
        deck = [Card(suit, rank) for suit in Suit for rank in Rank]
        self.random.shuffle(deck)
        return deck
    
    def deal_hole_cards(self):
        ''' Deal 2 hole cards to each player '''
        for _ in range(2):
            for player in self.players:
                player.add_card(self.deck.pop())
        
                
    def deal_community_cards(self, num_cards):
        ''' Pop num_cards cards from the deck and add to community cards '''
        for _ in range(num_cards):
            self.community_cards.append(self.deck.pop())
            
    def post_blinds(self):
        ''' Posts blinds differently for 2 and >2 player games '''
        if self.num_players == 2:
            small_blind = self.dealer_position
            big_blind = (self.dealer_position + 1) % 2
            
            print(f"Player {small_blind} is the small blind.")
            print(f"Player {big_blind} is the big blind.")
            
            bets = [small_blind, big_blind]
            self.ask_for_blinds(bets)
        else:
            small_blind = (self.dealer_position + 1) % self.num_players
            big_blind = (self.dealer_position + 2) % self.num_players
            
            print(f"Player {small_blind} is the small blind")
            print(f"Player {big_blind} is the big blind")
            
    def ask_for_blinds(self, bets: List[int]):
        ''' Prompts for both blind bets '''
        small_blind = int(input(f"Player {bets[0]}, How much would you like to bet? (small blind) \n You have: {self.players[bets[0]].stack} \n"))
        big_blind = int(input(f"Player {bets[1]}, How much would you like to bet? It must be atleast 2x the small blind (${small_blind * 2}) (big blind) \n You have: {self.players[bets[1]].stack} \n"))
        while not (big_blind >= small_blind * 2):
            big_blind = int(input(f"Please enter a valid amount. It must be atleast 2x the small blind (${small_blind * 2}) \n"))

        try:
            self.pot += self.players[bets[0]].bet(small_blind)
            self.pot += self.players[bets[1]].bet(big_blind)
        except ValueError as e:
            print(e)    # TODO: Retry in the case where a player can't afford the bet
        
        print(f"Player {bets[0]} bet ${small_blind}.")
        print(f"Player {bets[1]} bet ${big_blind}")
        
            
    def betting_round(self):
        # ''' TODO: Implement betting round logic when client connectivity is here '''
        # for i in range(num_players):
        #     msg = int(input(f"Player {i}, how much would you like to bet?: $"))
        #     self.pot += msg
        #     print(f"Player {i} bet ${msg}")
        print("Begin betting round.\n")
    
    def play_hand(self):
        ''' Main game flow for each hand '''
        self.deal_hole_cards()  # Pre-flop 
        
        self.post_blinds()   # Small and big blinds (forced bets) 
        self.betting_round()    # First betting round takes place
        
        self.show_player_hands()   # TODO: Delete this when client functionality implemented

        print("Pre-flop completed") 
        print(f"Current pot is: ${self.pot}")
        

        
        self.deal_community_cards(3) # Flop
        self.print_cards(self.community_cards) 
        
        self.show_player_hands()   # TODO: Delete this when client functionality implemented
            
        self.betting_round()
        print("Flop completed") 
        print(f"Current pot is: ${self.pot}")

        
        self.deal_community_cards(1) # Turn
        self.print_cards(self.community_cards) 
        
        self.show_player_hands()   # TODO: Delete this when client functionality implemented
            
        self.betting_round()
        print("Turn completed") # Debug
        print(f"Current pot is: ${self.pot}")

        
        self.deal_community_cards(1) # River
        self.print_cards(self.community_cards) 
        
        self.show_player_hands()   # TODO: Delete this when client functionality implemented
            
        self.betting_round()
        print("River completed") # Debug
        print(f"Final pot is: ${self.pot}")

        
        # Determine winner and print result
        result = self.determine_winner()
        if isinstance(result[0], list):
            # Multiple winners
            winners, hand_rank = result
            print(f"It's a tie! Pot split evenly amongst the winners: {', '.join(str(player) for player in winners)}")
            print (f"Winning hand: {hand_rank.name}")
            
            for player in winners:
                player.win(self.pot / self.num_players)
        else:
            # Single winner
            winner, hand_rank = result
            print(f"The winner is Player {winner}")
            print(f"Winning hand: {hand_rank.name}")
            self.players[winner].win(self.pot)
                
        self.reset_game() 

    def reset_game(self):
        ''' Resets the game state 
            Creates and shuffles a new deck
            Resets community cards
            Resets players hands
            Resets pot amount
            Moves dealer to next position'''
        self.deck = self.create_deck()
        self.community_cards = []
        for player in self.players:
            player.clear_cards()
        self.pot = 0
        self.move_dealer_position()
        self.small_blind = 0
        self.big_blind = 0
    
    def move_dealer_position(self):
        '''Moves dealer incrementer to next position
           Even though the server is handling all dealing, 
           it is still important to keep track of the dealer 
           to determine proper betting order'''
        self.dealer_position = (self.dealer_position + 1) % self.num_players
        
        
    def determine_winner(self):
        ''' Determine who wins the pot 
            Returns (player_index, HankRank.)'''
        player_hands= []
        for i, player in enumerate(self.players):
            best_hand = self.get_best_hand(player.hand + self.community_cards)
            player_hands.append((i, best_hand))
            
        # Create custom key function for sorting
        def hand_key(hand):
            hand_rank, cards = hand[1]
            
            # Adjust all ace-low straights to be lower than straights (as A=14)
            card_values = [card.rank.value for card in cards]
            if hand_rank == HandRank.STRAIGHT or HandRank.STRAIGHT_FLUSH and sorted(card_values) == [2,3,4,5,14]:
                card_values = [1,2,3,4,5]
                
            return (hand_rank.value, tuple(sorted(card_values, reverse=True)))
        
        # Sort each players best hand by HandRank (descending) and then by card values
        sorted_hands = sorted(player_hands, key=hand_key, reverse=True)
        
        # Check for ties (TODO: At the moment, ties = both win)
        winners = [sorted_hands[0]]
        for hand in sorted_hands[1:]:
            if hand_key(hand) == hand_key(winners[0]):
                winners.append(hand)
            else:
                break
            
        if len(winners) == 1:
            return winners[0][0], winners[0][1][0]     # Single winner: (player_index, hand_rank)
        else:
            return [w[0] for w in winners], winners[0][1][0]    # Multiple winners: ([player_indices], hand_rank)

    
    def get_best_hand(self, cards: List[Card]) -> Tuple[HandRank,List[Card]]:
        ''' Finds the best possible 5-card hand from 7 cards '''
        best_hand = (HandRank.HIGH_CARD, [])
        for hand in combinations(cards, 5):     # From each possible 5-card combination
            hand_rank = self.rank_hand(hand)     # Find the rank
            if hand_rank > best_hand[0] or (hand_rank == best_hand[0] and self.compare_same_rank(hand, best_hand[1], hand_rank) > 0):
                best_hand = (hand_rank, list(hand))
        return best_hand
            
    def rank_hand(self, hand: List[Card]) -> HandRank:
        ''' Ranks a 5-card hand and determines the best possible poker hand 
        
            TODO: Once client-server interaction is implemented, consider having
            Players pick their own best poker hands. (instead of trying all possible combinations)'''
            
        if self.is_royal_flush(hand):
            return HandRank.ROYAL_FLUSH
        if self.is_straight_flush(hand):
            return HandRank.STRAIGHT_FLUSH
        if self.is_four_of_a_kind(hand):
            return HandRank.FOUR_OF_A_KIND
        if self.is_full_house(hand):
            return HandRank.FULL_HOUSE
        if self.is_flush(hand):
            return HandRank.FLUSH
        if self.is_straight(hand):
            return HandRank.STRAIGHT
        if self.is_three_of_a_kind(hand):
            return HandRank.THREE_OF_A_KIND
        if self.is_two_pair(hand):
            return HandRank.TWO_PAIR
        if self.is_pair(hand):
            return HandRank.PAIR
        return HandRank.HIGH_CARD
    
    def is_royal_flush(self, hand: List[Card]) -> bool:
        return self.is_straight_flush(hand) and  sum(card.rank.value for card in hand) == 60
    
    def is_straight_flush(self, hand: List[Card]) -> bool:
        return self.is_flush(hand) and self.is_straight(hand)
    
    def is_four_of_a_kind(self, hand: List[Card]) -> bool:
        ranks = [card.rank.value for card in hand]
        return 4 in Counter(ranks).values()
    
    def is_full_house(self, hand: List[Card]) -> bool:
        ranks = [card.rank.value for card in hand]
        return sorted(Counter(ranks).values()) == [2, 3]

    def is_flush(self, hand: List[Card]) -> bool:
        return len(set(card.suit for card in hand)) == 1
    
    def is_straight(self, hand: List[Card]) -> bool:
        ranks = sorted(set(card.rank.value for card in hand))
        if len(ranks) == 5:
            if ranks[-1] - ranks[0] == 4:
                return True
            if ranks == [2, 3, 4, 5, 14]:  # Ace-low straight case
                return True
        return False
    
    def is_three_of_a_kind(self, hand: List[Card]) -> bool:
        ranks = [card.rank.value for card in hand]
        return 3 in Counter(ranks).values()
    
    def is_two_pair(self, hand: List[Card]) -> bool:
        ranks = [card.rank.value for card in hand]
        return list(Counter(ranks).values()).count(2) == 2
    
    def is_pair(self, hand: List[Card]) -> bool:
        ranks = [card.rank.value for card in hand]
        return 2 in Counter(ranks).values()
            
        
    def compare_same_rank(self, hand1: List[Card], hand2: List[Card], rank: HandRank) -> int:
        ranks1 = sorted([card.rank.value for card in hand1], reverse=True)
        ranks2 = sorted([card.rank.value for card in hand2], reverse=True)
        
        if rank in [HandRank.FOUR_OF_A_KIND, HandRank.FULL_HOUSE, HandRank.THREE_OF_A_KIND, HandRank.TWO_PAIR, HandRank.PAIR]:
            counts1 = Counter(ranks1)
            counts2 = Counter(ranks2)
            values1 = sorted(counts1.items(), key=lambda x: (x[1], x[0]), reverse=True)
            values2 = sorted(counts2.items(), key=lambda x: (x[1], x[0]), reverse=True)
            return self.compare_lists([v[0] for v in values1], [v[0] for v in values2])
        return self.compare_lists(ranks1, ranks2)
    
    def compare_lists(self, list1: List[int], list2: List[int]) -> int:
        for a, b in zip(list1, list2):
            if a > b:
                return 1
            if a < b:
                return -1
        return 0
    
    def print_cards(self, hand: List[Card]):
        ''' Prints any cards passed to it. Useful for showing the community cards '''
        rows = ['','','','','']
        for card in hand:
            if (card.rank.value > 10):  # Display A, J, Q, K instead of value
                x = card.rank.name
            else:
                x = card.rank.value
            rows[0] += ' ___  '  # Top line of the card
            rows[1] += '|{} | '.format(str(x).ljust(2))
            rows[2] += '| {} | '.format(str(card.suit.value))
            rows[3] += '|_{}| '.format(str(x).rjust(2, '_'))
        
        for row in rows:
            print(row)
        rows.clear()
    
    def show_player_hands(self):
        ''' Shows each players hand, used for debugging '''
        for i in range(self.num_players):
            print(f"Player {i}:")
            rows = ['','','','','']
            for card in self.players[i].hand:
                if (card.rank.value > 10):  # Display A, J, Q, K instead of value
                    x = card.rank.name
                else:
                    x = card.rank.value
                rows[0] += ' ___  '  # Top line of the card
                rows[1] += '|{} | '.format(str(x).ljust(2))
                rows[2] += '| {} | '.format(str(card.suit.value))
                rows[3] += '|_{}| '.format(str(x).rjust(2, '_'))
            
            for row in rows:
                print(row)
            rows.clear()
            
                
    
    

# Main game loop
if __name__ == "__main__":
    num_players = int(input("Enter the number of players (2-9): "))
    while not (2 <= num_players <= 9):
        num_players = int(input("Enter a valid number of players (2-9): "))
    game = TexasHoldEm(num_players)
    game.play_hand()