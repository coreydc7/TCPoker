import socket
import threading
# import logging # Do we have to use logger?

HOST = '0.0.0.0' # Listen on any available IP address
PORT = 65432 # Non-privileged ports are > 1023
MAX_CONNECTIONS = 4

# Handle each client connection
def handle_client(conn, addr):
    print(f'Connected by {addr}')
    try:
        with conn:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                conn.sendall(data)
    finally:
        print(f"Connection from {addr} closed")

# Main server function
def start_server():
    # use 'with' so we dont have to explicitly close the socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen(MAX_CONNECTIONS)
        print("Created listening socket")
        
        threads = []
        try:
            while True:
                conn, addr = s.accept()
                if len(threads) >= MAX_CONNECTIONS:
                    print(f"Max connections reached. Rejecting connection from {addr}")
                    conn.close()
                    continue
                thread = threading.Thread(target=handle_client, args=(conn, addr))
                thread.start()
                threads.append(thread)
                
                # Clean up finished threads
                threads = [t for t in threads if t.is_alive()]
        except KeyboardInterrupt:
            print("Server shutting down.")
        finally:
            # Wait for all threads to complete
            for thread in threads:
                thread.join()


if __name__ == "__main__":
    start_server()