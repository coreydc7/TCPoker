import sys
import selectors
import json
import io
import struct

class Message:
    ''' Handles multiple messages per connection by resetting state after each response.
        Resets state after a _write(), and after creating a response'''
        
    def __init__(self, selector, sock, addr, request, debug):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self.request = request
        self._recv_buffer = b""
        self._send_buffer = b""
        self._request_queued = False
        self._jsonheader_len = None
        self.jsonheader = None
        self.response = None
        self.debug = debug
        
    def _set_selector_events_mask(self, mode):
        """Set selector to listen for events: mode is 'r', 'w', or 'rw'."""
        if self.sock is None:
            return # Socket is closed
        
        if mode == "r":
            events = selectors.EVENT_READ
        elif mode == "w":
            events = selectors.EVENT_WRITE
        elif mode == "rw":
            events = selectors.EVENT_READ | selectors.EVENT_WRITE
        else:
            raise ValueError(f"Invalid events mask mode {repr(mode)}.")
        self.selector.modify(self.sock, events, data=self)
        
    def _read(self):
        try:
            # Should be ready to read
            data = self.sock.recv(4096)
        except BlockingIOError:
            # Resource temporarily unavailable (errno EWOULDBLOCK)
            pass
        else:
            if data:
                self._recv_buffer += data
            else:
                raise RuntimeError("Peer closed.")
        
            
    def _write(self):
        if self._send_buffer:
            if(self.debug): print("\nsending", repr(self._send_buffer), "to", self.addr)
            try:
                # Should be ready to write
                sent = self.sock.send(self._send_buffer)
            except BlockingIOError:
                # Resource temporarily unavailable (errno EWOULDBLOCK)
                pass
            else:
                # Once the message is sent, drain the sent buffer
                self._send_buffer = self._send_buffer[sent:]
                if sent and not self._send_buffer:
                    self._reset_state()

    def _json_encode(self, obj, encoding):
        return json.dumps(obj, ensure_ascii=False).encode(encoding)

    def _json_decode(self, json_bytes, encoding):
        tiow = io.TextIOWrapper(
            io.BytesIO(json_bytes), encoding=encoding, newline=""
        )
        obj = json.load(tiow)
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
        message = message_hdr + jsonheader_bytes + content_bytes
        return message
    
    def _process_response_json_content(self):
        content = self.response
        if "connect" in content:
            print(f"{content.get('connect')} \n {content.get('players')}")
        if "result" in content:
            print(f'\n{content.get("result")}')           
        if "debug" in content and self.debug:
            print(f'\n{content.get("debug")}')    
            
    def process_events(self, mask):
        ''' Main entry point and handler '''
        try:
            if mask & selectors.EVENT_READ:
                self.read()
            if mask & selectors.EVENT_WRITE:
                self.write()
        except Exception as e:
            print(f"Error processing events: {e}")
            self.close()
    def read(self):
        self._read()

        if self._jsonheader_len is None:
            self.process_protoheader()

        if self._jsonheader_len is not None:
            if self.jsonheader is None:
                self.process_jsonheader()

        if self.jsonheader:
            if self.response is None:
                self.process_response()

    def write(self):
        if not self._request_queued:
            self.queue_request()
        self._write()

        if self._request_queued and not self._send_buffer:
            # Set selector to listen for r/w events
            self._set_selector_events_mask("rw")
                
    def close(self):
        if(self.debug): print("\nclosing connection to", self.addr)
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

    def queue_request(self):
        ''' First task for the client when performing write() '''
        content = self.request["content"] 
        content_type = self.request["type"]
        content_encoding = self.request["encoding"]
        req = {
            "content_bytes": self._json_encode(content, content_encoding),
            "content_type": content_type,
            "content_encoding": content_encoding,
        }
        message = self._create_message(**req)
        self._send_buffer += message # Request message is appended to the send buffer, which is sent via _write()
        self._request_queued = True # Set state variable so queue_request() isnt called again by main while True

    def process_protoheader(self):
        hdrlen = 2
        if len(self._recv_buffer) >= hdrlen:
            self._jsonheader_len = struct.unpack(
                ">H", self._recv_buffer[:hdrlen]
            )[0]
            self._recv_buffer = self._recv_buffer[hdrlen:]

    def process_jsonheader(self):
        hdrlen = self._jsonheader_len
        if len(self._recv_buffer) >= hdrlen:
            self.jsonheader = self._json_decode(
                self._recv_buffer[:hdrlen], "utf-8"
            )
            self._recv_buffer = self._recv_buffer[hdrlen:]
            for reqhdr in (
                "byteorder",
                "content-length",
                "content-type",
                "content-encoding",
            ):
                if reqhdr not in self.jsonheader:
                    raise ValueError(f'Missing required header "{reqhdr}".')

    def process_response(self):
        content_len = self.jsonheader["content-length"]
        if not len(self._recv_buffer) >= content_len:
            return # Waits until all data is received
        
        data = self._recv_buffer[:content_len]
        self._recv_buffer = self._recv_buffer[content_len:]
        
        encoding = self.jsonheader["content-encoding"]
        try:
            self.response = self._json_decode(data, encoding)
        except json.JSONDecodeError as e:
            if(self.debug): print(f"\nJSONDecodeError: {e}")
            self.close()
            return
        if(self.debug): print("\nreceived response", repr(self.response), "from", self.addr)
        self._process_response_json_content()
        
        self._reset_state()
             
    def _reset_state(self):
        ''' Reset the message state for the next request '''
        self._recv_buffer = b""
        self._jsonheader_len = None
        self.jsonheader = None
        # self.request = None
        self.response_created = False