# TCPoker

This is a simple Texas Hold'em game implemented over TCP using Python

**How to play:**
1. **Start the server:** Run the `server.py` script. 
        Required flags are: -i <IP address of server>, -p <Listening port>
        Optional flags are: [-h] - Displays help information, [-v] - Verbose outputs, displays useful information such as connection/disconnection events, socket changes, data sent and received, etc. 
2. **Connect clients:** Run the `client.py` script on 2-9 different machines or terminals. -h will display usage tips and required flags.
3. **Play the game:** Server deals each player two hole cards at the start of the round. Players take turns betting each time a new community card is dealt face-up on the board. The goal is to make the best five-card poker hand using any combination of hole cards and community cards. Whoever has the best hand, wins the pot. 

**Technologies used:**
* Python
* Sockets

**Additional resources:**
* [Link to Python documentation]
* [Link to sockets tutorial]
    
