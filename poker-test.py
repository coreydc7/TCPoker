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
        
    def test_evaluate_hand_royal_flush(self):
        ''' Test evaluate hand to verify Royal flush beats a Straight flush '''
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

    def test_tie_breaker_flush(self):
        ''' Test tie-breaker scenario for a flush '''
        self.game.best_hands[self.game.players[0]] = ['A♥', 'K♥', '9♥', '5♥', '2♥']    # Flush
        self.game.best_hands[self.game.players[1]] = ['A♦', 'K♦', '9♦', '6♦', '3♦']    # Higher flush

        evaluated_hands = {}
        for player in self.game.players:
            evaluated_hands[player] = self.game.evaluate_hand(self.game.best_hands[player])

        # Sort players by their evaluated hand ranking and relevant cards for breaking ties
        sorted_players = sorted(evaluated_hands.items(), key=lambda x: x[1], reverse=True)

        # First player in list is the winner
        winner_player = sorted_players[0][0]
        # Player 2 should win due to higher kicker
        self.assertEqual(winner_player, self.game.players[1])  

    def test_tie_breaker_full_house(self):
        ''' Test tie-breaker scenario for a full house '''
        self.game.best_hands[self.game.players[0]] = ['K♠', 'K♣', 'K♦', 'J♠', 'J♣']    # Higher three-of-a-kind
        self.game.best_hands[self.game.players[1]] = ['Q♠', 'Q♣', 'Q♦', 'A♠', 'A♣']   

        evaluated_hands = {}
        for player in self.game.players:
            evaluated_hands[player] = self.game.evaluate_hand(self.game.best_hands[player])

        # Sort players by their evaluated hand ranking and relevant cards for breaking ties
        sorted_players = sorted(evaluated_hands.items(), key=lambda x: x[1], reverse=True)

        # First player in list is the winner
        winner_player = sorted_players[0][0]
        # Player 1 should win due to higher three-of-a-kind
        self.assertEqual(winner_player, self.game.players[0])  

    def test_tie_breaker_exact_tie(self):
        ''' Test tie-breaker scenario for an exact tie (full house, with the same tie-breaking cards) '''
        self.game.best_hands[self.game.players[0]] = ['K♠', 'K♣', 'K♦', '5♥', '5♥'] 
        self.game.best_hands[self.game.players[1]] = ['K♠', 'K♣', 'K♦', '5♠', '5♠'] 

        evaluated_hands = {}
        for player in self.game.players:
            evaluated_hands[player] = self.game.evaluate_hand(self.game.best_hands[player])

        # Sort players by their evaluated hand ranking and relevant cards for breaking ties
        sorted_players = sorted(evaluated_hands.items(), key=lambda x: x[1], reverse=True)

        winner_hand_info = sorted_players[0][1]
        loser_hand_info = sorted_players[1][1]

        hand_rankings = [
            "High Card", "One Pair", "Two Pair", "Three of a Kind", 
            "Straight", "Flush", "Full House", "Four of a Kind", 
            "Straight Flush", "Royal Flush"
        ]

        winning_hand_name = hand_rankings[winner_hand_info[0]]

        self.assertEqual(winning_hand_name, "Full House")
        self.assertEqual(winner_hand_info, loser_hand_info)

# suits = ['♠', '♥', '♦', '♣']
# ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
if __name__ == '__main__':
    unittest.main()