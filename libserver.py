import sys
import selectors
import json
import io
import struct
import logging

logging.basicConfig(
    filename='server.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ClientDisconnectException(Exception):
    ''' Custom exception to handle expected client disconnects vs unexpected client disconnects '''
    pass

class Message:
    ''' Handles multiple messages per connection by resetting state after each response.
        Resets state after a _write(), and after creating a response'''
    
    def __init__(self, selector, sock, addr, game_state, debug):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self._recv_buffer = b""
        self._send_buffer = b""
        self._jsonheader_len = None
        self.jsonheader = None
        self.request = None
        self.response_created = False
        self.debug = debug
        self.game_state = game_state
        
    def _set_selector_events_mask(self, mode):
        ''' Set selector to listen for events: mode is 'r', 'w', or 'rw'. '''
        if mode == 'r':
            events = selectors.EVENT_READ
            if(self.debug): print("Socket switched to r")
        elif mode == 'w':
            events = selectors.EVENT_WRITE
            if(self.debug): print("Socket switched to w")
        elif mode == 'rw':
            events = selectors.EVENT_READ | selectors.EVENT_WRITE
            if(self.debug): print("Socket switched to rw")
        else:
            raise ValueError(f"Invalid events mask mode {repr(mode)}.")
        self.selector.modify(self.sock, events, data=self)
        
    def _read(self):
        try:
            # Should be ready to read
            data = self.sock.recv(4096)
        except BlockingIOError:
            # Resource temporarily unavailable (errno EWOULDBLOCK)
            ''' This is a temporary error, skipped using pass so select() will eventually
            call us again. When the socket would block, for example waiting on the network
            or other end of the connection (its peer)'''
            pass
        else:
            if data:
                self._recv_buffer += data
            else:
                # No data to read means that peer disconnected
                raise ClientDisconnectException("Client Disconnected.")
            
    def _write(self):
        ''' Writes contents of send_buffer '''
        if self._send_buffer:
            if(self.debug): print("sending", repr(self._send_buffer), "to", self.addr)
            try:
                # Should be ready to write
                sent = self.sock.send(self._send_buffer)
            except BlockingIOError:
                # Resource temporarily unavailable (errno EWOULDBLOCK)
                pass
            else:
                self._send_buffer = self._send_buffer[sent:]
                if sent and not self._send_buffer:
                    # Once the message is sent, send buffer is drained
                    # Turn socket back into reading mode for next message
                    self._set_selector_events_mask("r") 
                    # Reset state to handle the next message
                    self._reset_state()
                    
    def _json_encode(self, obj, encoding):
        return json.dumps(obj, ensure_ascii=False).encode(encoding)
    
    def _json_decode(self, json_bytes, encoding):
        tiow = io.TextIOWrapper(
            io.BytesIO(json_bytes), encoding=encoding, newline=""
        )
        try:
            obj = json.load(tiow)
        except json.JSONDecodeError as e:
            print(f"JSONDecodeError during decoding (check header field lengths): {e}")
            obj = None
        tiow.close()
        return obj
    
    def _create_message(
        self, *, content_bytes, content_type, content_encoding
    ):
        jsonheader = {
            "byteorder": sys.byteorder,
            "content-type": content_type,
            "content-encoding": content_encoding,
            "content-length": len(content_bytes),
        }
        jsonheader_bytes = self._json_encode(jsonheader, "utf-8")
        message_hdr = struct.pack(">H", len(jsonheader_bytes))
        return message_hdr + jsonheader_bytes + content_bytes    # Assemble message
    
    def _create_response_json_content(self):
        action = self.request.get("action")
        
        if action == "join":
            if self in self.game_state.connected_clients:
                content = {"result": "Already joined table"}
            elif (len(self.game_state.connected_clients) < self.game_state.game.num_players):
                self.game_state.connected_clients.append(self)
                self.game_state.broadcast_to_others(f'{self.addr} has joined the table', self.game_state.connected_clients.index(self),tag='debug')
                content = {"connect": "Welcome to TCPoker!","players": f'You are Player #{self.game_state.connected_clients.index(self) + 1}\nThere are {len(self.game_state.connected_clients)}/{self.game_state.game.num_players} player(s) connected.'}
            else:
                content = {"result": 'Unable to join the table, there are to many players already at table.',"players": f'There are currently {len(self.game_state.connected_clients)} players connected.'}
        
        elif action == "status":
            result = ''
            for client in self.game_state.connected_clients:
                player_idx = self.game_state.connected_clients.index(client)
                is_ready = 'ready' if self.game_state.game.check_player_ready(player_idx) else 'not ready'
                result += f'Player {player_idx} is {is_ready}\n'
            content = {"result": result}
        
        elif action == "ready":
            self.game_state.game.set_player_ready(self.game_state.connected_clients.index(self))
            content = {"result": f'Marked Player {self.game_state.connected_clients.index(self) + 1} as ready.'}

        else:
            content = {"result": f"Unknown action: '{action}'."}
                
        content_encoding = "utf-8"
        content_bytes = self._json_encode(content, content_encoding)
        response = {
            "content_bytes": content_bytes,
            "content_type": "text/json",
            "content_encoding": content_encoding,
        }
        return response
        
    
    def process_events(self, mask):
        ''' Main entry point and handler '''
        try:
            if mask & selectors.EVENT_READ:
                self.read()
            if mask & selectors.EVENT_WRITE:
                self.write()
        except ClientDisconnectException:
            # if theres no data to read, then read will raise a ClientDisconnectException. 
            # Ensure we close the socket if client disconnects 
            self.close()
        except Exception as e:
            print(f"Error processing events {e}")
            self.close()
            
    def read(self):
        self._read()
        
        if self._jsonheader_len is None:
            self.process_protoheader()
        
        if self._jsonheader_len is not None:
            if self.jsonheader is None:
                self.process_jsonheader()
                
        if self.jsonheader:
            if self.request is None:
                self.process_request()
                
    def write(self):
        if self.request and not self.response_created:
                self.create_response()
        self._write()
        
    def close(self):
        message = f"Server has closed connection to {self.addr}"
        print(message)
        logging.info(message)
        self.game_state.broadcast_message(f'{self.addr} has left the table.', tag="debug")
        
        try:
            self.game_state.connected_clients.remove(self)
        except ValueError as e:     # Occurs when a client didn't fully join successfully
            pass
        
        try:
            self.selector.unregister(self.sock)
        except Exception as e:
            print(
                f"error: selector.unregister() exception for",
                f"{self.addr}: {repr(e)}",
            )
            
        try:
            self.sock.close()
        except OSError as e:
            print(
                f"error: socket.close() exception for",
                f"{self.addr}: {repr(e)}",
            )
        finally:
            # Delete reference to socket object for garbage collection
            self.sock = None
            
    def process_protoheader(self):
        hdrlen = 2 # Hard-coded length. 2-byte integer in network (big-endian) byte order
        if len(self._recv_buffer) >= hdrlen:
            ''' struct.unpack is used to read the value, decode it, and store it in 
            self._jsonheader_len. Handles conversions such as endianness and 
            interprets bytes as packed binary data '''
            self._jsonheader_len = struct.unpack( 
                ">H", self._recv_buffer[:hdrlen]
            )[0]
            # after processing, remove it from the receive buffer
            self._recv_buffer = self._recv_buffer[hdrlen:] 
            
    def process_jsonheader(self):
        ''' Decodes and deserializes the JSON header into a dictionary '''
        hdrlen = self._jsonheader_len
        if len(self._recv_buffer) >= hdrlen:
            self.jsonheader = self._json_decode(
                self._recv_buffer[:hdrlen], "utf-8"
            )
            # removes itself from the receive buffer after processing
            self._recv_buffer = self._recv_buffer[hdrlen:] 
            for reqhdr in (
                "byteorder",
                "content-length",
                "content-type",
                "content-encoding",
            ):
                if reqhdr not in self.jsonheader:
                    raise ValueError(f'Missing required header "{reqhdr}".')
                
    def process_request(self):
        content_len = self.jsonheader["content-length"]
        if not len(self._recv_buffer) >= content_len:
            return
        data = self._recv_buffer[:content_len]  # Save message content to the "data" var
        self._recv_buffer = self._recv_buffer[content_len:]     # Remove from buffer
        if self.jsonheader["content-type"] == "text/json":  # Decode and deserialize JSON
            encoding = self.jsonheader["content-encoding"]
            self.request = self._json_decode(data, encoding)
            if(self.debug): print("received request", repr(self.request), "from", self.addr)
        else:
            # Binary or unknown content-type
            self.request = data 
            print(
                f'received {self.jsonheader["content-type"]} request from', 
                self.addr,
            )
        # Set selector to listen for write events, we're done reading
        # A response can now be created and written to the socket
        self._set_selector_events_mask("w")
        
    def create_response(self):
        ''' Calls other methods to create a response for writing, and appends it to _send_buffer '''
        response = self._create_response_json_content()
        message = self._create_message(**response)
        self._send_buffer += message
        self.response_created = True
            
        # self._reset_state()
        
    def create_message(self, message, tag="result"):
        ''' Creates a formatted message for writing, and appends it to _send_buffer '''
        content = {tag: message} 
        content_encoding = "utf-8"
        content_bytes = self._json_encode(content, content_encoding)
        response = {
            "content_bytes": content_bytes,
            "content_type": "text/json",
            "content_encoding": content_encoding,
        }
        return self._create_message(**response)
            
    def _reset_state(self):
        ''' Reset the message state for the next request '''
        self._recv_buffer = b""
        self._jsonheader_len = None
        self.jsonheader = None
        self.request = None
        self.response_created = False    