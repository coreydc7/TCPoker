import random
from enum import Enum, IntEnum
from dataclasses import dataclass, field
from typing import List, Tuple
from collections import Counter
from itertools import combinations
from functools import total_ordering
import asyncio

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
    def __init__(self, num_players, GameState, starting_stack=100, seed=None):
        self.num_players = num_players
        self.random = random.Random(seed)
        self.deck = self.create_deck()
        self.community_cards = []
        self.players = [Player(starting_stack) for _ in range(num_players)]
        self.pot = 0
        self.dealer_position = 0
        self.small_blind = 0
        self.big_blind = 0
        self.GameState = GameState
        self.bet_futures = {}
        
    async def play_hand(self):
        ''' Main game flow for every hand '''
        await self.post_blinds()  # Small and big blinds (forced bets)
        self.deal_hole_cards()  # Pre-flop

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
    
    async def post_blinds(self):
        ''' Posts blinds differently for 2 and >2 player games '''
        if self.num_players == 2:
            small_blind = self.dealer_position
            big_blind = (self.dealer_position + 1) % 2
            
            await self.GameState.broadcast("broadcast", f"{self.GameState.connected_clients[small_blind][2]} is the small blind, and {self.GameState.connected_clients[big_blind][2]} is the big blind.")
            await asyncio.sleep(0.1)
            bets = [small_blind, big_blind]
            await self.ask_for_blinds(bets)
        else:
            small_blind = (self.dealer_position + 1) % self.num_players
            big_blind = (self.dealer_position + 2) % self.num_players
            
            await self.GameState.broadcast("broadcast", f"{self.GameState.connected_clients[small_blind][2]} is the small blind, and {self.GameState.connected_clients[big_blind][2]} is the big blind.")
            await asyncio.sleep(0.1)
            bets = [small_blind, big_blind]
            await self.ask_for_blinds(bets)
            
    async def ask_for_blinds(self, bets: List[int]):
        ''' Prompts for both blinds bets '''
        small_blind = bets[0]
        big_blind = bets[1]
        
        await self.GameState.broadcast_client(
            small_blind,
            "make_bet",
            f"You are the small blind, how much would you like to bet? You currently have {self.players[small_blind].stack}: "
        )
        await self.GameState.broadcast_others(
            "broadcast",
            f"Waiting for {self.GameState.connected_clients[small_blind][2]} to make a move...", 
            self.GameState.connected_clients[small_blind][0]
        )
        
        while(self.pot == 0):
            await asyncio.sleep(0.1)
        
        await self.GameState.broadcast_client(
            big_blind,
            "make_bet",
            f"You are the big blind, how much would you like to bet? You currently have {self.players[big_blind].stack}: "
        )
        await self.GameState.broadcast_others(
            "broadcast", 
            f"Waiting for {self.GameState.connected_clients[big_blind][2]} to make a move...", 
            self.GameState.connected_clients[big_blind][0]
        )
    
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
        
        card = ''
        for row in rows:
            card += row
        rows.clear()
        return card
    
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
        