import unittest
from server import Player, TCPokerServer

class TestPoker(unittest.TestCase):
    def setUp(self):
        self.game = TCPokerServer()
        self.game.game_active = True
        client1 = Player("adam", None)
        client2 = Player("betty", None)
        self.game.players.append(client1)
        self.game.players.append(client2)

        # suits = ['♠', '♥', '♦', '♣']
        # ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
        
    def test_evaluate_royal_flush(self):
        self.game.best_hands[self.game.players[0]] = ['A♥', 'K♥', 'Q♥', 'J♥', 'T♥']    # Royal flush
        self.game.best_hands[self.game.players[1]] = ['2♥', '3♥', '4♥', '5♥', '6♥']    # Straight flush
        
        evaluated_hands = {}
        for player in self.game.players:
            evaluated_hands[player] = self.game.evaluate_hand(self.game.best_hands[player])

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

        self.assertEqual(winning_hand_name, "Royal Flush")
        self.assertEqual(winner_player, self.game.players[0])

        self.assertEqual(losing_hand_name, "Straight Flush")
        self.assertEqual(loser_player, self.game.players[1])



if __name__ == '__main__':
    unittest.main()