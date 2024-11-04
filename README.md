# TCPoker

This is a simple Texas Hold'em game implemented over TCP using Python

**How to play:**
1. **Start the server:** Run the `server.py` script:
* Required flags are: -i (host IP), -p (Listening port)
* Optional flags are: [-h] (Displays help information)
2. **Connect clients:** Run the `client.py` script on 2 separate terminals or machines. 
* Required flags are: -i (IP address of server), -p (Listening port of server), -u (Custom username/identifier)
* Optional flags are: [-h] (Displays help information)
  
3. **Play the game: (work in progress)** \
   Once enough clients are connected and readied up, the server will automatically start the game of Texas Hold'em. The game is already well defined inside of the class found in poker_offline.py, and the flow is as follows: 
* Beginning at the pre-flop, the server will request an ante from each client for them to buy into the hand. After every ante is collected, it will deal each client their hole cards and send them to the client. This marks the start of the first betting round.
* During each betting round, each client will take turns entering their bet action. All other clients wait for their turn, and messages indicating the other clients actions are broadcast to every client. Each client has the option to 'check', 'call', 'raise', or 'fold' their hand.
* After each betting round, a new card is dealt onto the table, and a new round of betting begins. There are four total betting rounds, where players will have to leverage poker strategy to win the game.
* At the end of the fourth betting round, the player who can assemble the best 5 card poker hand from the 5 community cards and their two hole cards will win all the bet money in the pot.
4. **Sprint Progress** \
  Sprint 2
* `client.py`: Client script is able to be started and connect to the server. Logs connection and disconnection attempts in console. Clients are able to communicate with the server through various actions ['join', 'exit', 'ready', 'status'] and process/display the servers response. Client connections are persistent, and will stay connected until the 'exit' command is entered, which will trigger a graceful disconnect, closing the socket and selector. This allows for the client to send many messages and process their responses, all over a single socket connection. Each client is handled asynchronously, so incoming messages from the server do not interrupt client input. All server messages are displayed above the line prompting for client input, which ensures a smooth command-line UI. The flag '-v' displays debug information, and shows debug messages sent from the server, such as other clients connection and disconnection attempts. 
* `server.py`: Server script is able to be started and listen for incoming connections over a port. Handles multiple client connections simultaneously. Logs connection and disconnection events in console. Server initializes the Texas Hold'em game, and maintains a list of connected clients and their associated gamestates. Once all clients have readied up, the server begins the game. Server is able to process incoming JSON messages and individually send out responses, or broadcast a message to all other connected clients. Automatically broadcasts debug information to all clients, such as other clients connections/disconnections. Handles 'join' and 'exit' (connection/disconnection) requests from the client gracefully.
* `poker_offline.py`: Poker script is functional and able to be executed via `python poker_offline.py`. Allows for entering the number of players, and then proceeds to start a Texas Hold'em Poker game utilizing the game flow and structure outlined above. It is entirely offline, so player's hands and all other debug information is printed to the console. Player input information is gathered locally through the console. All game functions are working, including the function to algorithmically determine the best 5-card poker hand from the 7-card list of community cards + hole cards. This serves as an extremely solid base to begin implementation on the online functionalities, in a separate file `poker.py`.

Sprint 3 \
* notes: Switched to a fully asynchronous client and server model using asyncio (previously only client was asynchronous). This was much harder than anticipated, and much of Sprint 3 was spent debugging race conditions. Instead of using low-level socket operations, asyncio provides high-level abstractions utilizing StreamWriter/StreamReader to create a TCP server and handle reading/writing socket operations. In order to handle IO-bound networking, threading or asyncio can be utilized. Through my research, I decided to use asyncio, as it can scale much better and wouldn't require creating 9 additional threads if I wanted to handle a 9-player Poker game. 
* `server.py`: Server script manages game state using GameState class. This class utilizes broadcast methods to broadcast game state updates to a specific client, every client except a certain client, or to all connected clients. Handles client disconnections gracefully.
* `client.py`: Client renders game state updates depending on JSON message contents. As the game state is managed by the GameState class, a consistent game state is broadcast to all clients. Each client has a ClientState class to hold information about the state of the client, such as whether it is that clients turn or not. The server synchronizes turn information across all clients, and clients who are waiting receive a "Waiting for X to make a move..." message. Upon initial connection to a server, clients are prompted to submit their own custom username which is used to identify that connected client and track their game state.

Sprint 4 \
* notes: I refactored the entire codebase one day after the Sprint 3 deadline. The functionality is mostly the same, but I was able to do the same thing with much less and simpler code, as I already had a good idea of the execution flow. I also was able to eliminate a race condition that was causing the server to hang only when clients connected/readied up in a specific order. 
  
**Protocol (work in progress)** \
Updated 11/4/2024 \
The game flow has been outlined under "Play the game", and the internal protocol for executing this game flow is as follows:
* When the client script executes, it automatically joins the game, and sends a 'username' message signaling their custom username: ```{ 
                "username": "xyz" 
        }```
* The server broadcasts messages to all client to inform them of new connections, disconnections, etc. Or it broadcasts a message to a single client if they requested specific information ```{
                "broadcast": "Adam has joined the game."
        }```
* The client sends commands to the server once it has connected. These include commands such as 'status','ready','exit','bet','check','raise','fold',etc. ```{
                 "command": "status"
  }```
  
* Once the required number of players have readied up, the server begins the game, and asks each client to pay the ante in order to join the hand ```{
                "action": "collect_ante",
                "amount": 10
        }```
* After the antes are paid, The server then sends each client their private hole cards. All 'cards' are an instance of the Card class - Card(suit, rank): ```{
                "action": "deal_hole_cards",
                "cards": [Card(suit, rank), Card(suit, rank)]
        }```
* For the blind bets and all betting rounds, a similar action can be used with a different message. Server requests a bet amount from the client: ```{
                "action": "request_bet",
                "prompt": "Your move: {check, call, raise, fold}.",
                "current_bet": 20,
                "client_balance": 100
        }```
* Client response to the betting request: ```{
                "action": "player_action",
                "player_id": 1,
                "move": "raise",
                "amount": 50
        }```
* The action taken by each player will be broadcast from the server to all clients: ```{
                "action": "broadcast_action",
                "player_id": 1,
                "move": "raise",
                "amount": 50,
                "message": "Player 1 raises by 50."
        }```
* After each betting round, the server will deal community cards and send what they are to each client. There are three stages of dealing community cards (flop, turn, river): ```{
                "action": "deal_community_cards",
                "stage": "flop",
                "cards": [Card(suit, rank), Card(suit, rank), Card(suit, rank)],
                "message": "Flop: "cards" have been dealt."
        }```
* After the final betting round, the server will either automatically determine the winner, or prompt each player to assemble and submit their best 5-card poker hand for determining the winner. I am going back-and-forth on this step a lot, so this will likely change. Example end of game winner announcement, from server: ```{
                "action": "game_end",
                "winner": {
                        "player_id": 2,
                        "hand": [Card, Card, Card, Card, Card],
                },
                "pot": 200,
                "message": "Player 2 wins the pot of 200 with a Royal Flush!."
        }```
* Invalid commands from clients that would raise errors could be prevented on the client-side, or through an error message sent by the server. ```{
                "action": "error",
                "code": 400,
                "message": "Invalid action. Please choose from {check, call, raise, fold}"
        }```
                        
        
        
**Technologies used:**
* Python
* Sockets

**Additional resources:**
* [Link to Python documentation](https://docs.python.org/3/)
* [Link to sockets tutorial](https://docs.python.org/3/howto/sockets.html)
    
