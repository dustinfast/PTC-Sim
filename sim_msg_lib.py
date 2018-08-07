""" An Edge Message Protocol (EMP) messaging system using the Apache Qpid
    messaging API. Supports acting as a msg sender, receiver, or broker.

    Message Specification:
        Adheres to EMP V4, as specified in msg_spec/S-9354.pdf
        
    Author:
        Dustin Fast, 2018
"""

import struct
import binascii
from qpid.messaging import Connection


class Message(object):
    """ A representation of a message, including it's raw EMP form.
        Supports construction from both raw and human-readable forms.
    """
    def __init__(self):
        """ Constructs an empty message object. Use from_human() or from_raw()
            to populate message contents.
        """
        self.msg_type = None
        self.destination = None
        self.sender = None
        self.payload = None

    def from_human(self, msg_type, dest_addr, sender_addr, payload):
        """ Populates the message object from human parameters, converting 
            from human to raw format in the process.
                msg_type =      (int) Message Type. Ex: 6000
                dest_addr =     (str) Destination addr. Ex: 'arr.l.arr.IDNM'
                sender =        (str) Sender addr. Ex: 'arr.b:locop'
                payload =       (str) A '|' delimited list of fields, Ex:
                                      'TIME|arr:LOCOID|LAT|LONG|SPEED'
        """
        self.msg_type = msg_type
        self.destination = dest_addr
        self.sender = sender_addr
        self.payload = payload

        # Determine msg body size (i.e. payload length + room for 32 bit CRC)
        body_len = 3 + len(payload)

        ####################################################
        # Build the raw msg as big-endian using struct.pack,
        # noting that:
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
        send_req += struct.pack(">I", binascii.crc32(send_req))  # 32 bit CRC

    def from_raw(self, raw_msg):
        """ Populates the message object from it's raw/receved msg form, 
            converting from raw to human readable form in the process.
        """
        # Extract msg contents, noting that each raw_msg[i] is 1 byte 
        payload = ''
        for i in list(range(len(raw_msg[4:]))):
            payload += raw_msg[i]
        
        # Explode payload on '|'
        msg_content = payload.split('|')

        #TODO: populate self from msg_content based on msg type
        print(msg_content)
        

class MsgReceiver(object):
    """ The message receiver. Monitors the given queue at the specified 
        broker for messages.
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


class MsgSender(object):
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
        """ Sends the raw form of the given message (of type Message) through 
            the broker to the queue specified in the message. 
        """
        # Start a QPID session for the given destination, send the msg, then
        # close the session.
        sender = self.session.sender(message.destination)
        sender.send(message.packed_msg)
        sender.close()  
