import sys
import selectors
import json
import io
import struct

class Message:
    ''' Handles multiple messages per connection by resetting state after each response.
        Resets state after a _write(), and after creating a response'''
    
    def __init__(self, selector, sock, addr, debug):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self._recv_buffer = b""
        self._send_buffer = b""
        self._jsonheader_len = None
        self.jsonheader = None
        self.request = None
        self.response_created = False
        self.numPlayers = 0
        self.debug = debug
        
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
                raise RuntimeError("Peer closed.")
            
    def _write(self):
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
            if (self.numPlayers < 9):
                self.numPlayers += 1
                content = {"connect": "Welcome to TCPoker!","players": f'There are {self.numPlayers} player(s) connected.'}
            else:
                content = {"connect": 'Error: too many players already at table.',"players": f'There are currently {self.numPlayers} players connected.'}
        
        elif action == "status":
            content = {"result": 'TODO: Display all players and their ready status'}
        
        elif action == "ready":
            content = {"result": 'TODO: Mark the current player as ready.'}
        
        elif action == "exit":
            print(f"Disconnecting {self.addr}")
            self.close()
            return None
        
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
            
                
        
    
    def _create_response_binary_content(self):
        ''' Example handling binary actions '''
        # if(self.request[:6] == "negate" or "double"):   
        #     action, value = struct.unpack(">6si", self.request)
        #     action = action.decode("utf-8")
        #     result = b"result"
        #     result_num = 0
            
        #     if(action == "negate"):
        #         result_num = value * -1
        #     elif(action == "double"):
        #         result_num = value * 2
                
        #     result_content = struct.pack(">6si", result, result_num)
        #     response = {
        #         "content_bytes": result_content,
        #         "content_type": "binary/custom-server-binary-type",
        #         "content_encoding": "binary",
        #     }
            
        # else:
        #     response = {
        #         "content_bytes": b"First 10 bytes of request: "
        #         + self.request[:10],
        #         "content_type": "binary/custom-server-binary-type",
        #         "content_encoding": "binary",
        #     }
        # return response
        pass
    
    def process_events(self, mask):
        ''' Main entry point and handler '''
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()
            
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
        print("closing connection to", self.addr)
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
            ''' #struct.unpack is used to read the value, decode it, and store it in 
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
        ''' Calls other methods to create a response, depending on the content-type '''
        if self.jsonheader["content-type"] == "text/json":
            response = self._create_response_json_content()
        else:
            # Binary or unknown content-type
            response = self._create_response_binary_content()
       
        message = self._create_message(**response)
        self._send_buffer += message
        self.response_created = True
            
        self._reset_state()
            
    def _reset_state(self):
        ''' Reset the message state for the next request '''
        self._recv_buffer = b""
        self._jsonheader_len = None
        self.jsonheader = None
        self.request = None
        self.response_created = False