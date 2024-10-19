import unittest
from poker_offline import TexasHoldEm, Card, Suit, Rank, HandRank, Player

class TestPoker(unittest.TestCase):
    def setUp(self) -> None:
        self.game_2p = TexasHoldEm(2) 
    
    def test_dw_royal_flush(self):        
        self.game_2p.players[0].add_card(Card(Suit.HEARTS, Rank.A))
        self.game_2p.players[0].add_card(Card(Suit.HEARTS, Rank.K))
        
        self.game_2p.players[1].add_card(Card(Suit.SPADES, Rank.A))
        self.game_2p.players[1].add_card(Card(Suit.SPADES, Rank.Q))
        
        self.game_2p.community_cards = [
            Card(Suit.HEARTS, Rank.Q),
            Card(Suit.HEARTS, Rank.J),
            Card(Suit.HEARTS, Rank.TEN),
            Card(Suit.DIAMONDS, Rank.NINE),
            Card(Suit.CLUBS, Rank.EIGHT)
        ]
        
        winner, hand_rank = self.game_2p.determine_winner()
        self.assertEqual(winner, 0)     # Player 0 should win with a royal flush
        self.assertEqual(hand_rank, HandRank.ROYAL_FLUSH)
        
    def test_dw_lowstraight_vs_straight(self):  
        self.game_2p.reset_game()
              
        self.game_2p.players[0].add_card(Card(Suit.CLUBS, Rank.A))
        self.game_2p.players[0].add_card(Card(Suit.CLUBS, Rank.TWO))
        
        self.game_2p.players[1].add_card(Card(Suit.CLUBS, Rank.SIX))
        self.game_2p.players[1].add_card(Card(Suit.CLUBS, Rank.SEVEN))
        
        self.game_2p.community_cards = [
            Card(Suit.CLUBS, Rank.THREE),
            Card(Suit.CLUBS, Rank.FOUR),
            Card(Suit.CLUBS, Rank.FIVE),
            Card(Suit.DIAMONDS, Rank.NINE),
            Card(Suit.CLUBS, Rank.EIGHT)
        ]          
                             
        winner, hand_rank = self.game_2p.determine_winner()
        self.assertEqual(winner, 1) # Player 1 should win with a higher straight than Player 0's Ace-low straight
        self.assertEqual(hand_rank, HandRank.STRAIGHT_FLUSH)
        
        
        
        
if __name__ == '__main__':
    unittest.main()