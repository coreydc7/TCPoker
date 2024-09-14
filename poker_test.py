import unittest
from texas1 import TexasHoldEm, Card, Suit, Rank, HandRank

class TestPoker(unittest.TestCase):
    def setUp(self):    # Create a game with 2 players for testing
        self.game = TexasHoldEm(2) 
        
    def test_dw_royal_flush(self):
        self.game.players = [
            [Card(Suit.HEARTS, Rank.A), Card(Suit.HEARTS, Rank.K)],
            [Card(Suit.SPADES, Rank.A), Card(Suit.SPADES, Rank.Q)]
        ]
        self.game.community_cards = [
            Card(Suit.HEARTS, Rank.Q),
            Card(Suit.HEARTS, Rank.J),
            Card(Suit.HEARTS, Rank.TEN),
            Card(Suit.DIAMONDS, Rank.NINE),
            Card(Suit.CLUBS, Rank.EIGHT)
        ]
        winner, hand_rank = self.game.determine_winner()
        self.assertEqual(winner, 0)     # Player 0 should win with a royal flush
        self.assertEqual(hand_rank, HandRank.ROYAL_FLUSH)
        
    def test_dw_lowstraight_vs_straight(self):
        self.game.players = [
            [Card(Suit.CLUBS, Rank.A), Card(Suit.CLUBS, Rank.TWO)],
            [Card(Suit.CLUBS, Rank.SIX), Card(Suit.CLUBS, Rank.SEVEN)]
        ]
        self.game.community_cards = [
            Card(Suit.CLUBS, Rank.THREE),
            Card(Suit.CLUBS, Rank.FOUR),
            Card(Suit.CLUBS, Rank.FIVE),
            Card(Suit.DIAMONDS, Rank.NINE),
            Card(Suit.CLUBS, Rank.EIGHT)
        ]                               
        winner, hand_rank = self.game.determine_winner()
        self.assertEqual(winner, 1) # Player 1 should win with a higher straight than Player 0's Ace-low straight
        self.assertEqual(hand_rank, HandRank.STRAIGHT)
        
        
        
        
if __name__ == '__main__':
    unittest.main()