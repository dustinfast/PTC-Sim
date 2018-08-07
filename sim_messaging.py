""" An Edge Message Protocol (EMP) messaging system, supports acting as a msg
    sender, receiver, or broker.

    Supports the following operations:
        broker - Acts to manage messaging queues necessary for transport.
        client - A receiver of messages
        server - A sender of messages

    Message Specification:
        Adheres to EMP version 4 (as specified in msg_spec/S-9354.pdf) using a
        variable header of size 
        

"""
import struct
import binascii
from time import time
from qpid.messaging import Connection


class Message(object):
    """ A representation of a message, including it's raw form.
        Supports bi-directional conversion between raw and human-readable forms.
    """
    def __init__(self):
        """ Constructs an empty message object.
        """
        self.msg_type = None        # Ex: 6000
        self.destination = None   # Ex: 'arr.l.arr.IDNM'
        self.sender = None       # Ex: 'arr.b:locop'
        self.payload = None          # Ex:  A string or pickled object
        self.raw_msg = None

    def from_human(self, msg_type, dest_addr, sender_addr, payload):
        """ Populates the message object from human parameters, converting 
            from human to raw format in the process.
        """
        self.msg_type = msg_type
        self.destination = dest_addr
        self.sender = sender_addr
        self.payload = payload

        # Determine secondary msg properties for use in building raw
        body_len = 3 + len(payload)  # Body size + room for 32 bit CRC
        pack_time = int(time())      # Unix time of msg creation

        ####################################################
        # Build the raw msg (big-endian) using struct.pack
        #  Note:
        #   B = unsigned char, 8 bits
        #   H = unisigned short, 16 bits
        #   I = unsigned int, 32 bits
        #   i = signed int, 32 bits

        # Build EMP "Common Header"
        send_req = struct.pack(">B", 4)  # 8 bit EMP header version
        send_req += struct.pack(">H", msg_type)  # 16 bit message type/ID
        send_req += struct.pack(">B", 1)  # 8 bit message version
        send_req += struct.pack(">B", 1)  # 8 bit flag denoting absolute time
        send_req += struct.pack(">I", body_len)[1:]  # 24 bit msg body size

        # Build EMP "Optional header"
        send_req += struct.pack(">i", 0)  # 32 bit Message number, 0 = no chunks
        send_req += struct.pack(">I", pack_time)  # 32 bit msg creation time

        # Build EMP "Variable Header"
        send_req += struct.pack(">B", 24)  # 8 bit "variable header" size
        send_req += struct.pack(">H", 120)  # 16 bit network TTL (seconds)
        send_req += struct.pack(">H", 0)  # 16 bit QoS, 0 = no preference
        send_req += sender_addr  # 64 byte (max) msg source addr string
        send_req += '\x00'  # null terminate msg source address
        send_req += dest_addr  # 64 byte (max) msg dest addr string
        send_req += '\x00'  # null terminate destination address
        
        # Build msg body
        send_req += payload  # Must be of size body_len - 32 bits

        # Build CRC footer
        send_req += struct.pack(">I", binascii.crc32(send_req))  # 32 bit CRC

    def from_raw(self, raw_msg):
        """ Populates the message object from it's raw/receved msg form, 
            converting from raw to human reable in the process.
        """
        assert(False)
        

class EMPReceiver(object):
    """ The EMP message receiver. Monitors the given queue at the specified 
        broker for EMP messages.
    """
    def __init__(self, broker_address, queue_name, refresh_rate=1):
        """
        """
        self.broker = broker_address
        self.queue = queue_name
        self.refresh = refresh_rate
        self.connection = None  # Populated on self.open()

    def open(self):
        """ Opens a connection to the broker.
            # TODO: Raises...
        """
        self.connection = Connection(self.broker)
        self.connection.open()
        self.session = self.connection.session()

    def close(self):
        """ Closes the connection with the broker.
        """
        self.session.close()
        self.connection.close()

    def get_next_msg(self, timeout=5):
        """ Blocks for the given timeout (seconds) while waiting for a new msg
            at self.queue.
            Raises Queue.Empty on timeout.
        """
        assert(False)


class EMPSender(object):
    """ The message sender. Sends msgs to the broker.
    """
    def __init__(self, broker_address):
        self.broker = broker_address
        self.connection = None  # Populated on self.open()

    def open(self):
        """ Opens a connection to the broker.
            # TODO: Raises...
        """
        self.connection = Connection(self.broker)
        self.connection.open()
        self.session = self.connection.session()

    def close(self):
        """ Closes the connection with the broker.
        """
        self.session.close()
        self.connection.close()

    def send_msg(self, message):
        """ Sends the given message (of type Message) through the broker to 
            the queue specified by the message. 
        """
        # Start new QPID session for the given destination, send the msg,
        # then close the session
        sender = self.session.sender(message.destination)
        sender.send(message.packed_msg)
        sender.close()  

class EMPBroker(object):
    """
    """
    assert(False)
