# TCPoker

This is a simple Texas Hold'em game implemented over TCP using Python

**How to play:**
1. **Start the server:** Run the `server.py` script. \
        Required flags are: -i (host IP), -p (Listening port), -c (Number of players, supports 2-9 player games) \
        Optional flags are: [-h] (Displays help information), [-v] - Verbose outputs, displays useful information such as connection/disconnection events, socket changes, data sent and received, etc. 
2. **Connect clients:** Run the `client.py` script on 2-9 different machines or terminals. \
        Required flags are: -i (IP address of server), -p (Listening port of server) \
        Optional flags are: [-h] (Displays help information), [-v] - Verbose outputs, displays useful information such as connection/disconnection events or data being sent and received. 
3. **Play the game: (work in progress)** Server deals each player two hole cards at the start of the round. Players take turns betting each time a new community card is dealt face-up on the board. The goal is to make the best five-card poker hand using any combination of hole cards and community cards. Whoever has the best hand, wins the pot. \
Currently, poker.py contains all the logic for the texas hold'em game itself (which is fully functional offline). Clients are able to communicate with the server via a very simple messaging protocol, which can be used to send commands such as 'join'/'status'/'ready'/'exit' and process their responses. Client connections are persistent, and they can exchange any number of commands before disconnecting with the 'exit' command. 

**Technologies used:**
* Python
* Sockets

**Additional resources:**
* [Link to Python documentation](https://docs.python.org/3/)
* [Link to sockets tutorial](https://docs.python.org/3/howto/sockets.html)
    
