# %%
import random
# Set up the constants:
HEARTS = chr(9829)  # '♥'
DIAMONDS = chr(9830)  # '♦'
SPADES = chr(9824)  # '♠'
CLUBS = chr(9827)  # '♣'

deck = []
for suit in (HEARTS, DIAMONDS, SPADES, CLUBS):
    for rank in range(2, 11):
        deck.append((str(rank), suit))  # Add the numbered cards
    for rank in ('J', 'Q', 'K', 'A'):
        deck.append((rank, suit))  # Add the face and ace cards.
random.shuffle(deck)
print(deck)
print()
