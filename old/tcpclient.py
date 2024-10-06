import socket
import time

class TCPClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None
    
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print(f'Connected to server at {self.host}:{self.port}')
        except socket.error as e:
            print(f"Connection failed: {e}")
            self.socket = None
    
    def disconnect(self):
        if self.socket:
            self.socket.close()
            print(f"Disconnected from server at {self.host}:{self.port}")
            self.socket = None
            
    def send_data(self, data):
        if self.socket:
            try:
                self.socket.sendall(data.encode())
                print(f"Sent data: {data}")
            except socket.error as e:
                print(f"Failed to send data: {e}")
                self.disconnect()
                
    def receive_data(self):
        if self.socket:
            try:
                data = self.socket.recv(1024)
                if data:
                    decode = data.decode()
                    print(f"Received data: {decode}")
                    return decode
                else:
                    print(f"Nothing to receive from server")
                    self.disconnect()
            except socket.error as e:
                print(f"Failed to receive data: {e}")
                self.disconnect()
        return None
    
# Main client function
def main():
    HOST = '10.0.0.221'       # MODIFY THIS LINE TO USE THE SERVER'S IP ADDRESS
    PORT = 65432        # Port used by the server
    
    client = TCPClient(HOST,PORT)
    
    # Attempt to connect with retries
    max_retries = 3
    for attempt in range(max_retries):
        client.connect()
        if client.socket:
            break
        print(f"Retrying connection in 5 seconds (attempt {attempt + 1}/{max_retries})")
        time.sleep(5)
        
    if not client.socket:
        print(f"Failed to connect after {max_retries} tries")
        return
    
    # Connection is successful after this point
    while True:
        msg = input("Enter message to send (or exit to end):")
        if(msg == 'exit'):
            break
        client.send_data(msg)
        response = client.receive_data()
    
    # Disconnect
    client.disconnect()
    

if __name__ == "__main__":
    main()