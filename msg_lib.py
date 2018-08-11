""" A messaging library for sending and receiving fixed-format, variable-
    length-header messages according to the Edge Message Protocol (EMP) 
    specification as defined in msg_spec/S-9354.pdf. See README.md for 
    implementation specific information.

    Contains classes for msg sending and msg queue watching over TCP/IP

    Author:
        Dustin Fast, 2018
"""

import struct
import socket
import binascii
import ConfigParser
from Queue import Empty, Full  # Queue.Empty and Queue.Full exception types

# Init conf
config = ConfigParser.RawConfigParser()
config.read('conf.dat')

# Import conf data
BROKER = config.get('messaging', 'broker')
MAX_TRIES = config.get('misc', 'max_retries')
SEND_PORT = int(config.get('messaging', 'send_port'))
FETCH_PORT = int(config.get('messaging', 'fetch_port'))
MAX_MSG_SIZE = int(config.get('messaging', 'max_msg_size'))


class MsgQueue:
    """ A message queue with push pop, peek, remove, is_empty, and item_count.
    """
    def __init__(self, maxsize=None):
        self._items = []            # Container
        self.maxsize = maxsize      # Max size of self._items
        # TODO: self.lock = False   # Threadsafe lock

        # Validate maxsize and populate with defaultdata
        if maxsize and maxsize < 0:
                raise ValueError('Invalid maxsize.')

    def push(self, item):
        """ Adds an item to the back of queue.
        Raises Queue.Full if queue at max capacity,
        """
        if self.is_full():
            raise Full()
        self._items.append(item)

    def pop(self):
        """ Pops front item from queue and returns it.
            Raises Queue.Empty if queue empty on pop().
        """
        if self.is_empty():
            raise Empty
        d = self._items[0]
        self._items = self._items[1:]
        return d
    
    def peek(self, n=0):
        """ Returns the nth item from queue front, leaving queue unchanged.
            Raises IndexError if no nth item.
            Raises Queue.Empty if queue empty.
        """
        if self.is_empty():
            raise Empty

        try:
            return self._items[n]
        except IndexError:
            raise IndexError('No element at position ' + str(n))

    def remove(self, n=0):
        """ Removes the nth item from the queue and shuffles other msgs forward.
            Raises IndexError if no nth item.
        """ 
        try:
            self._items[n]
        except IndexError:
            raise IndexError('No element at position ' + str(n))
        
        self._items = self._items[0:n] + self._items[n + 1:]

    def is_empty(self):
        """ Returns true iff queue empty.
        """
        return self.item_count() == 0

    def is_full(self):
        """ Returns true iff queue at max capacity.
        """
        return self.maxsize and self.item_count() >= self.maxsize

    def item_count(self):
        return len(self._items)


class Message(object):
    """ A representation of a message, including it's raw EMP form. Contains
        static functions for converting between tuple and raw EMP form.
    """
    def __init__(self, msg_content):
        """ Constructs a message object from the given content - either a
            well-formed EMP msg string, or a tuple of the form:
                (Message Type - ex: 6000,
                 Sender address - ex: 'arr.b:locop',
                 Destination address - ex: 'arr.l.arr.IDNM',
                 Payload - ex: { key: value, ... }
                )
                Note: All other EMP fields are static in this implementation.
        """
        if type(msg_content) == str:
            self.raw_msg = msg_content
            msg_content = self._to_tuple(msg_content)
        else:
            if type(msg_content) != tuple or len(msg_content) != 4:
                raise Exception('Msg content is an unexpected type or length.')
            self.raw_msg = self._to_raw(msg_content)

        self.msg_type = msg_content[0]
        self.sender_addr = msg_content[1]
        self.dest_addr = msg_content[2]
        self.payload = msg_content[3]

    @staticmethod
    def _to_raw(msg_tuple):
        """ Given a msg in tuple form, returns a well-formed EMP msg string.
        """
        msg_type = msg_tuple[0]
        sender_addr = msg_tuple[1]
        dest_addr = msg_tuple[2]
        payload = msg_tuple[3]
        payload_str = str(payload)

        # Calculate body size (i.e. payload length + room for the 32 bit CRC)
        body_size = 4 + len(payload_str)

        # Calculate size of variable portion of the "Variable Header",
        # i.e. len(source and destination strings) + null terminators.
        var_headsize = len(sender_addr) + len(dest_addr) + 2

        # Build the raw msg (#TODO: big-endian?) using struct.pack, noting:
        #   B = unsigned char, 8 bits
        #   H = unsigned short, 16 bits
        #   I = unsigned int, 32 bits
        #   i = signed int, 32 bits
        try:
            # Pack EMP "Common Header"
            raw_msg = struct.pack(">B", 4)  # 8 bit EMP header version
            raw_msg += struct.pack(">H", msg_type)  # 16 bit message type/ID
            raw_msg += struct.pack(">B", 1)  # 8 bit message version
            raw_msg += struct.pack(">B", 0)  # 8 bit flag, all zeroes here.
            raw_msg += struct.pack(">I", body_size)[1:]  # 24 bit msg body size

            # Pack EMP "Variable Header"
            raw_msg += struct.pack(">B", var_headsize)  # 8 bit variable header size
            raw_msg += struct.pack(">H", 120)  # 16 bit network TTL (seconds)
            raw_msg += struct.pack(">H", 0)  # 16 bit QoS, 0 = no preference
            raw_msg += sender_addr  # 64 byte (max) msg source addr string
            raw_msg += '\x00'  # null terminate msg source address
            raw_msg += dest_addr  # 64 byte (max) msg dest addr string
            raw_msg += '\x00'  # null terminate destination address
            
            # Pack msg body
            raw_msg += payload_str  # Variable size
            raw_msg += struct.pack(">i", binascii.crc32(raw_msg))  # 32 bit CRC
        except:
            raise Exception("Msg format is invalid")

        # debug
        # print('ENCODED MSG - ')
        # print('type: ' + str(msg_type))
        # print('body size: ' + str(body_size))
        # print('sender: ' + sender_addr)
        # print('dest: ' + dest_addr)
        # print('payload: ' + payload_str)
        
        return raw_msg

    @staticmethod
    def _to_tuple(raw_msg):
        """ Returns a tuple representation of the msg contained in raw_msg.
        """
        # Validate raw_msg
        if not raw_msg or len(raw_msg) < 20:  # 20 byte min msg size
            # print('raw: "' + raw_msg + '"')  # debug
            raise Exception("Invalid message format")

        # Ensure good CRC
        msg_crc = struct.unpack(">i", raw_msg[-4::])[0]  # last 4 bytes
        raw_crc = binascii.crc32(raw_msg[:-4])

        if msg_crc != raw_crc:
            raise Exception("CRC Mismatch - message may be corrupt.")

        # Unpack msg fields, noting that unpack returns results as a tuple
        msg_type = struct.unpack('>H', raw_msg[1:3])[0]  # bytes 1-2
        vhead_size = struct.unpack('>B', raw_msg[8:9])[0]  # byte 8

        # Extract sender, destination, and playload based on var header size
        vhead_end = 13 + vhead_size
        vhead = raw_msg[13:vhead_end]
        vhead = vhead.split('\x00')  # split on terminators for easy extract
        sender_addr = vhead[0]
        dest_addr = vhead[1]
        payload = raw_msg[vhead_end:len(raw_msg) - 4]  # -4 moves before CRC

        # Turn the payload into a python dictionary
        try:
            payload = eval(payload)
        except:
            raise Exception('Msg payload not of form { key: value, ... }')

        # debug
        # print('DECODED MSG - ')
        # print('type: ' + str(msg_type))
        # print('vhead size: ' + str(vhead_size))
        # print('vhead: ' + str(vhead))
        # print('sender: ' + sender_addr)
        # print('dest: ' + dest_addr)
        # print('payload: ' + str(payload))

        return (msg_type, sender_addr, dest_addr, payload)


class Client(object):
    """ Exposes send_msg() and fetch_msg() interfaces to broker clients.
    """
    def __init__(self, 
                 broker=BROKER,
                 broker_send_port=SEND_PORT,
                 broker_fetch_port=FETCH_PORT):
        """
        """
        self.broker = broker
        self.send_port = broker_send_port
        self.fetch_port = broker_fetch_port

    def send_msg(self, message):
        """ Sends the given message (of type Message) over TCP/IP to the 
            broker. The msg will wait at the broker in the queue specified by
            the message to be fetched by other broker clients.
        """
        # Establish socket connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.broker, self.send_port))
        print('Connected to broker ' + self.broker + ':' + str(self.send_port))

        # Send the msg repeatedly until the recipient gives 'OK' or 'FAIL'
        while True:
            sock.send(message.raw_msg.encode('hex'))  # Send msg
            response = sock.recv(MAX_MSG_SIZE).decode()  # get response

            if response == 'RETRY':
                print('Msg failed to send... Retrying.')
            else:
                if response == 'OK':
                    print('Msg sent succesfully')  # debug
                elif response == 'FAIL':  
                    print('Msg failed to send... No retry requested.')  # debug
                else:
                    print('Invalid response received... Aborting.')  # debug
                break

        sock.close()

    def fetch_next_msg(self, queue_name):
        """ Fetches a msg from the broker.queue_name. The message is removed 
            from the broker on success.
            Raises Queue.Empty if specified queue is empty.
            Returns a Message.
        """
        # Establish socket connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.broker, self.fetch_port))
        print('Connected to broker ' + self.broker + ':' + str(self.fetch_port))

        # Send fetch request until receipt of 'EMPTY', 'FAIL', or a valid msg.
        recv_tries = 0
        while True:
            recv_tries += 1
            sock.send(queue_name.encode())  # Send queue_name
            response = sock.recv(MAX_MSG_SIZE).decode()  # get response

            if response == 'OK':
                sock.send('READY'.encode())  # Send "READY to receive"
                raw_msg = sock.recv(MAX_MSG_SIZE).decode()
                try:
                    msg = Message(raw_msg.decode('hex'))
                except Exception as e:
                    errstr = 'Transfer failed due to ' + str(e)
                    if recv_tries < MAX_TRIES:
                        print(errstr + '... Will retry.')
                        e = 'RETRY'.encode()
                        sock.send(e)
                        continue
                    else:
                        print(errstr + '... Retries exhausted.')
                        sock.send('FAIL'.encode())
                        break
                print('Msg fetch succesful')  # debug
                return msg
            elif response == 'EMPTY':
                raise Empty()
            else:
                print('Invalid response received... Aborting.')  # debug
            break

        sock.close()
