# TCPoker

This is a simple Texas Hold'em game implemented over TCP using Python

**How to play:**
1. **Start the server:** Run the `server.py` script:
* Required flags are: -p (Listening port)
* Optional flags are: [-h] (Displays help information) [-s] (Enables automatic hand solver -- Players no longer need to assemble their own best 5-card poker hand from their 2 hole cards + 5 community cards, instead an algorithm will determine what their best possible hand is.)
2. **Connect clients:** Run the `client.py` script on 2 separate terminals or machines. 
* Required flags are: -i (IP address of server), -p (Listening port of server)
* Optional flags are: [-h] (Displays help information)
  
3. **Play the game:** \
   Once two clients have connected and readied up, the server will automatically start the game of Texas Hold'em. The game flow is as follows: 
* Beginning at the pre-flop, the server will request an ante from each client for them to buy into the hand. After every ante is collected, it will deal each client their hole cards and send them to the client. This marks the start of the first betting round.
* During each betting round, each client will take turns entering their bet action. All other clients wait for their turn, and messages indicating the other clients actions are broadcast to every client. Each clients available moves are dymanically displayed to them.
* After each betting round, a new card is dealt onto the table, and a new round of betting begins. There are four total betting rounds, where players will have to leverage poker strategy to win the game.
* At the end of the fourth betting round, the player who can assemble the best 5 card poker hand from the 5 community cards and their two hole cards will win all the bet money in the pot.

**Final Project Assessment** \
* Brief roadmap for this project \
While I am proud of the final submission for this project, I did not achieve all of the goals I originally set for this project, and had to change the scope of my initial idea. The first thing I would add to this project would be increasing the game size to support poker games of up to 9 players. This wouldn't be difficult to implement, but it was just easier to test my program when I only had to worry about 2 concurrent players. Next I would add persistent saving for players stack amounts. So if someone joined using the username "adam" and won $200, they would be able to connect back to the server the next day, login using their same username, and have their earned money available in their stack. Of course, this would then lead into adding a user authentication system to verify users. For this system I would add username/password registration, password requirements, password resets, email authentication, password hashing, rate limiting, CAPTCHA, and other security features. The saved data would be stored in a MySQL database, and should be encrypted. I would then address the security vulnerabilites that my program introduces by communicating via plain-text JSON via the methods outlined in my Sprint 5 Security/Risk evaluation. Only after I had implemented this secure backend for the project would I be comfortable putting it online and creating a frontend web UI for the project. 
* Retrospective on overall project \
I am very proud with this project, as I struggled a lot and it turned out great. My 81 commits,
5,627 lines of code added, and 4,409 deletions shows just how many times I had to refactor parts of this project. Here's my overall retrospective of this project, including what went right and what I could improve on. To begin, I believe my incremental approach to developent benefitted me greatly, as I knew what I wanted to do for this project early and began building an offline poker game to make sure I had the logic down first. This allowed me to focus a lot on building the client/server architecture, and I knew exactly what I wanted the client/server interaction to be like before I even started them. \
Once I got to the networking part of this project, I believe my decision to go with asyncio was absolutely the correct choice. Asyncio allowed for reliable and consistent client handling, and solved the issues I was having with raw socket programming following programming assignment #3. Asyncio provided everything I was looking for, including handling the TCP connections, their buffers and streams, allowing for non-blocking I/O, while being efficient and scalable. After getting my asyncio server running well, I struggled a lot with implementing a clean client-side UI. I was really set on messages being received above the clients input prompt, and this proved difficult to implement inside of the terminal. I spent about a week fiddling around with curses to create two separate windows, one for receiving server messages and one for sending client messages. I finally settled on using Prompt Toolkit, as this allowed me to start the input() command in a separate asyncio task, and have it stay at the bottom even when printing server messages to the terminal. Once I found out how to dynamically refresh the prompt displayed (to dynamically indicate which commands the client can perform), this turned out to be exactly what I was looking for and I'm glad I stuck with it. \
However, there is certainly much that I could improve on. To begin, I had better modularity in my code when I separated the poker game logic itself and the TCP server. I began by having my server play my offline poker game, but ended up combining the two during my last refactor to make it simpler as it was Sprint 4 and I was concerned I was not going to end up with a playable game. After slowly adding the poker game logic into the TCP server, the file ended up at 650 lines, which is not very modular. I felt like I did a good job documenting my logic with comments, as I was able to come back to this project and work on it without forgetting what stuff does. However, I still would like to separate the poker logic and networking logic to make it easier to read. I also believe that I could have done better testing throughout the entire span of my project. The poker-test.py file only really came to be during the last Sprint, and I was just executing the code myself for testing. It would've been much better if I did unit testing from the beginning, used mock objects for doing network integration testing, and done other test-driven development ideas such as looking at my code coverage. Overall I am glad that I struggled so much with this project, from socket programming, to learning what asyncio was and writing my first asyncio application, to figuring out how to implement a clean client-side UI. I feel like I am a much better and more confident programmer, as I am less scared of failure.

 **Sprint Progress** \
  Sprint 2
* `client.py`: Client script is able to be started and connect to the server. Logs connection and disconnection attempts in console. Clients are able to communicate with the server through various actions ['exit', 'ready', 'status'] and process/display the servers response. Client connections are persistent, and will stay connected until the 'exit' command is entered, which will trigger a graceful disconnect, closing the socket and selector. This allows for the client to send many messages and process their responses, all over a single socket connection. Each client is handled asynchronously, so incoming messages from the server do not interrupt client input. All server messages are displayed above the line prompting for client input, which ensures a smooth command-line UI. The flag '-v' displays debug information, and shows debug messages sent from the server, such as other clients connection and disconnection attempts. 
* `server.py`: Server script is able to be started and listen for incoming connections over a port. Handles multiple client connections simultaneously. Logs connection and disconnection events in console. Server initializes the Texas Hold'em game, and maintains a list of connected clients and their associated gamestates. Once all clients have readied up, the server begins the game. Server is able to process incoming JSON messages and individually send out responses, or broadcast a message to all other connected clients. Automatically broadcasts debug information to all clients, such as other clients connections/disconnections. Handles 'join' and 'exit' (connection/disconnection) requests from the client gracefully.
* `poker_offline.py`: Poker script is functional and able to be executed via `python poker_offline.py`. Allows for entering the number of players, and then proceeds to start a Texas Hold'em Poker game utilizing the game flow and structure outlined above. It is entirely offline, so player's hands and all other debug information is printed to the console. Player input information is gathered locally through the console. All game functions are working, including the function to algorithmically determine the best 5-card poker hand from the 7-card list of community cards + hole cards. This serves as an extremely solid base to begin implementation on the online functionalities, in a separate file `poker.py`.

Sprint 3 
* notes: Switched to a fully asynchronous client and server model using asyncio (previously only client was asynchronous). This was much harder than anticipated, and much of Sprint 3 was spent debugging race conditions. Instead of using low-level socket operations, asyncio provides high-level abstractions utilizing StreamWriter/StreamReader to create a TCP server and handle reading/writing socket operations. In order to handle IO-bound networking, threading or asyncio can be utilized. Through my research, I decided to use asyncio, as it can scale much better and wouldn't require creating 9 additional threads if I wanted to handle a 9-player Poker game. 
* `server.py`: Server script manages game state using GameState class. This class utilizes broadcast methods to broadcast game state updates to a specific client, every client except a certain client, or to all connected clients. Handles client disconnections gracefully.
* `client.py`: Client renders game state updates depending on JSON message contents. As the game state is managed by the GameState class, a consistent game state is broadcast to all clients. Each client has a ClientState class to hold information about the state of the client, such as whether it is that clients turn or not. The server synchronizes turn information across all clients, and clients who are waiting receive a "Waiting for X to make a move..." message. Upon initial connection to a server, clients are prompted to submit their own custom username which is used to identify that connected client and track their game state.

Sprint 4 
* notes: Most of Sprint 4 was spent continuing to learn the intricacies of asyncio. As this is something new for me, there were several things I was doing incorrectly that were causing unexpected behavior. Although I spent a lot of time refactoring code, in the end I was able to successfully polish the execution flow setup by Sprint 3. I found out how to better handle the clients prompt_toolkit, so the clients command-line UI dynamically updates the list of commands the client is allowed to send. I found a good method for handling player turns and transitioning between the different stages of poker using asyncio Events. I also found out how to handle starting the poker game concurrently alongside the listening and sending of messages by utilizing asyncio Tasks. Overall, merging the poker game and my asyncio client/server has come together quite nicely during this sprint. The poker game is playable from start to finish, and supports playing multiple rounds (although I still need to implement proper folding mechanics).
* `server.py`: Merged the state of the server and state of the Poker game under a central class, TCPokerServer. This class manages every aspect of the poker game state, and updates based on messages received from the clients and pre-defined poker logic. The server handles client commands for all stages of the poker game, and constantly updates the clients about the current state through broadcast messages and updating the list of valid commands the client is allowed to send. The server validates user input by updating this list of valid commands for the client, as well as checking to make sure clients have enough money to bet. Once the final betting round has concluded and both clients have sent in their 'hand' commands, the server's determine_winner() function evaluates which 5-card poker hand wins using poker logic. Currently, a winner is only determined after the final betting round, and folding hands isn't fully implemented yet. After the game, players are notified of the winner, and it automatically goes back into the lobby stage. The server cleans up it state, and both players can ready up to play another round of poker. This provides players with the option to play another round, or 'exit' to disconnect from the game.
* `client.py`: The client-side UI has greatly improved this sprint to be more user-friendly. Information about the game board, player information, and game status are displayed as messages above the client's input prompt. The client's input prompt always displays the valid commands the client can send, so the player knows what moves they are allowed to make. This provides clear and intuitive controls for players to interact with the game.

Sprint 5
* `server.py`: Fixed various bugs such as refunding a player when their opponent disconnects in the middle of the game and player folding. Added final features such as splitting the pot when an exact tie occurs (extremely rare, but handles cases where the best 5-card hand is the community card pool). Improved error messages across the board when a player performs an invalid bet action, such as not raising by 2x the current bet or betting more than their stack. Implemented optional '-s' flag, which will enable the automatic hand solver. This algorithmically determines each players best 5-card poker hand by brute-force ranking every 5-combination that can be made from the players 2 hand cards + 5 community cards. As this is a 7 choose 5 scenario, there is only 21 possible combinations. This makes brute-force a viable option and in practice it finds the best hand instantly.
* `client.py`: Not much changed with the client this sprint, mainly just improved the formatting by adding some new-lines to improve the UI experience.
* `poker-test.py`: Added unit tests for all edge-cases I identified earlier in testcases.txt. This file utilizes the python unittest library to perform unit-tests, verifying the functionality for edge-cases that would be impossible to test through normal play-testing. This also allows me to unit test specific functions I wrote, such as evaluate_hand(), get_best_hand(), and determine_winner().
* Security/Risk Evaluation: There are lots of security vulnerabilities in my program, and I wish I could've atleast added symmetric or asymmetric encryption to this program before the deadline. \
Currently, my program transmits data via plaintext JSON. This is vulnerable to attacks such as packet sniffing, man in the middle attacks, and replay attacks. I would address the first two attacks by implementing end-to-end encryption for all communications. I would address the vulnerability to replay attacks by adding message sequence numbers. \
Another problem is that the server has 0 protections against DDoS attacks. In order to address the vulnerability of DDoS and other flooding attacks, I would add rate-limiting to control the number of connection attempts/requests that are able to be sent from individual IP addresses. I would implement SYN cookies to prevent SYN flood attacks. 
  
  
**Protocol (work in progress)** \
The game flow has been outlined under "Play the game", and the internal protocol for executing this game flow is as follows:
* When the client script executes, it sends a 'username' message signaling the custom username chosen: ```{ 
                "username": "xyz" 
        }```
* The server broadcasts messages to all client to inform them of pretty much everything, such as connections, disconnections, game state updates such as who won or the pot, etc. It also handles messages sent to individual clients, such as their cards or stack amounts. ```{
                "broadcast": "Adam has joined the game."
        }```
* The client sends commands to the server once it has connected. These include commands such as 'status','ready','exit','bet','check','raise','fold',etc. ```{
                 "command": "status"
  }```
  
* Once the required number of players have readied up, the server begins the game, and asks each client to pay the ante in order to join the hand ```{
                "action": "collect_ante",
                "amount": 10
        }```
* After the antes are paid, The server then sends each client their private hole cards.: ```{
                "hand": ['T\u2665', 'T\u2663']
        }```
* For the blind bets and all betting rounds, a similar action can be used with a different message. Server requests a bet amount from the client: ```{
                "action": "collect_bets",
                "valid_actions": {call, raise, fold}.",
                "current_bet": 20,
                "to_call": 10,
                "pot": 20
        }```
* Invalid commands from clients that would raise errors could be prevented on the client-side, or through an error message sent by the server. ```{
                "error": "Invalid action. Please choose from {call, raise, fold}."
        }```
                        
        
        
**Technologies used:**
* Python
* Sockets
* Asyncio
* Prompt Toolkit

**Additional resources:**
* [Link to Python documentation](https://docs.python.org/3/)
* [Link to sockets tutorial](https://docs.python.org/3/howto/sockets.html)
    
