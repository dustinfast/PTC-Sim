""" PTC Sim's messaging library for sending and receiving Edge Message 
    Protocol(EMP) messages over TCP/IP. See README.md for implementation
    specific information.

    Author: Dustin Fast, 2018
"""

import Queue
import socket
from binascii import crc32
from struct import pack, unpack
from ConfigParser import RawConfigParser

# Init conf
config = RawConfigParser()
config.read('config.dat')

# Import conf data
REFRESH_TIME = int(config.get('application', 'refresh_time'))
BROKER = config.get('messaging', 'broker')
SEND_PORT = int(config.get('messaging', 'send_port'))
FETCH_PORT = int(config.get('messaging', 'fetch_port'))
MAX_MSG_SIZE = int(config.get('messaging', 'max_msg_size'))
NET_TIMEOUT = float(config.get('messaging', 'network_timeout'))

# Set default timeout for all sockets, including importers of this library
socket.setdefaulttimeout(NET_TIMEOUT)


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

        # Build the raw msg msg using struct.pack, noting that
        #   B = unsigned char, 8 bits
        #   H = unsigned short, 16 bits
        #   I = unsigned int, 32 bits
        #   i = signed int, 32 bits
        try:
            # Pack EMP "Common Header"
            raw_msg = pack(">B", 4)  # 8 bit EMP header version
            raw_msg += pack(">H", msg_type)  # 16 bit message type/ID
            raw_msg += pack(">B", 1)  # 8 bit message version
            raw_msg += pack(">B", 0)  # 8 bit flag, all zeroes here.
            raw_msg += pack(">I", body_size)[1:]  # 24 bit msg body size

            # Pack EMP "Variable Header"
            # 8 bit variable header size
            raw_msg += pack(">B", var_headsize)
            raw_msg += pack(">H", 120)  # 16 bit network TTL (seconds)
            raw_msg += pack(">H", 0)  # 16 bit QoS, 0 = no preference
            raw_msg += sender_addr  # 64 byte (max) msg source addr string
            raw_msg += '\x00'  # null terminate msg source address
            raw_msg += dest_addr  # 64 byte (max) msg dest addr string
            raw_msg += '\x00'  # null terminate destination address

            # Pack msg body
            raw_msg += payload_str  # Variable size
            raw_msg += pack(">i", crc32(raw_msg))  # 32 bit CRC
        except:
            raise Exception("Msg format is invalid")

        return raw_msg

    @staticmethod
    def _to_tuple(raw_msg):
        """ Returns a tuple representation of the msg contained in raw_msg.
        """
        # Validate raw_msg
        if not raw_msg or len(raw_msg) < 20:  # 20 byte min msg size
            raise Exception("Invalid message format")

        # Ensure good CRC
        msg_crc = unpack(">i", raw_msg[-4::])[0]  # last 4 bytes
        raw_crc = crc32(raw_msg[:-4])

        if msg_crc != raw_crc:
            raise Exception("CRC Mismatch - message may be corrupt.")

        # Unpack msg fields, noting that unpack returns results as a tuple
        msg_type = unpack('>H', raw_msg[1:3])[0]  # bytes 1-2
        vhead_size = unpack('>B', raw_msg[8:9])[0]  # byte 8

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
            Returns True if msg sent succesfully, else raises an issue-
            specific exception.
        """
        # Init socket and connect to broker
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.broker, self.send_port))

        # Send message and wait for a response
        sock.send(message.raw_msg.encode('hex'))
        response = sock.recv(MAX_MSG_SIZE).decode()
        sock.close()
        if response == 'OK':
            return True
        elif response == 'FAIL':
            raise Exception('Broker responded with FAIL.')
        else:
            raise Exception(
                'Unhandled response received from broker - Send aborted.')

    def fetch_next_msg(self, queue_name):  # TODO: Change to fetcher thread
        """ Fetches the next msg from queue_name from the broker and returns it,
            Raises Queue.Empty if specified queue is empty.
        """
        # Establish socket connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.broker, self.fetch_port))

        # Send queue name and wait for response
        sock.send(queue_name.encode())
        resp = sock.recv(MAX_MSG_SIZE)

        msg = None
        if resp == 'EMPTY':
            raise Queue.Empty  # No msg available to fetch
        else:
            msg = Message(resp.decode('hex'))  # Response is the msg

        sock.close()

        return msg

class Fetcher(object):
    # TODO: Fetcher
    pass

class Receiver(object):
    # TODO: Receiver (from broker)
    pass
