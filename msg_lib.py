""" An Apache Qpid API wrapper library for sending and receiving Edge Message
     Protocol (EMP) messages according to the following specification -

    Message Specification:
        EMP V4 (specified in msg_spec/S-9354.pdf) with fixed-format messages 
        containing a variable-length header section.

        EMP Field Implementation:
            |---------------------------------------------------|
            | Section  | Field / Value                          |
            |---------------------------------------------------|
            | Common   | EMP Header Version    : 4              |
            | Header   | Message Type/ID       : DYNAMIC        |
            |          | Message Version       : 1              |
            |          | Flags                 : 0              |
            |          | Body Size             : DYNAMIC        |
            |---------------------------------------------------|
            | Optional | Unused                                 |
            | Header   |                                        |
            |---------------------------------------------------|
            | Variable | Variable Header Size  : DYNAMIC        |
            | Length   | Network Time to Live  : 120            |
            | Header   | Quality of Service    : 0              |
            |          | Sender Address        : DYNAMIC        |
            |          | Destination Address   : DYNAMIC        |
            |----------|----------------------------------------|
            | Body     | Body/Data             : DYNAMIC        |
            |          | CRC                   : DYNAMIC        |
            |---------------------------------------------------|

        Fixed-Format Message Descriptions:
            |-------------------------------------------------------|
            | ID / Desc     | Data Element, by index                |
            |-------------------------------------------------------|
            | 6000:         | 0: A key/value string of the form     |
            | Loco status   |    {Send Time    : Unix Time,         |
            | message       |     Loco ID      : 4 digit integer,   |
            |               |     Speed        : 2 digit integer,   |
            |               |     Latitude     : Integer,           |
            |               |     Longitude    : Integer,           |
            |               |     Base Station : Integer            |
            |               |    }                                  |
            |-------------------------------------------------------|
            | 6001:         | 00: A key/value string of the form    |
            | BOS command   |    {Send Time    : Unix Time,         |
            | message for   |     Dest Loco ID : 4 digit integer,   |
            | locomitive    |     Command      : A well-formed cmd  |
            |               |                    Ex: 'speed(55)'    |
            |               |    }                                  |
            |-------------------------------------------------------|


    Author:
        Dustin Fast, 2018
"""

import struct
import binascii
from qpid.messaging import Connection


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
                # TODO: Exception type
                raise Exception('Invalid msg_content parameter recieved.')
            self.raw_msg = self._to_raw(msg_content)

        self.msg_type = msg_content[0]
        self.destination = msg_content[1]
        self.sender = msg_content[2]
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

        # Calculate size of variable part of the "Variable Header",
        # i.e. len(source and destination strings) + null terminators.
        var_headsize = len(sender_addr) + len(dest_addr) + 2

        # Build the raw msg (#TODO: big-endian?) using struct.pack, noting:
        #   B = unsigned char, 8 bits
        #   H = unsigned short, 16 bits
        #   I = unsigned int, 32 bits
        #   i = signed int, 32 bits

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

        return raw_msg

    @staticmethod
    def _to_tuple(raw_msg):
        """ Returns a tuple representation of the msg contained in raw_msg.
        """
        print('raw: "' + raw_msg + '"')  # debug

        # Ensure good CRC match
        msg_crc = struct.unpack(">i", raw_msg[-4::])[0]  # last 4 bytes
        raw_crc = binascii.crc32(raw_msg[:-4])

        if msg_crc != raw_crc:
            # TODO: Exception type
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
            # TODO: Exception type
            raise Exception('Invalid message payload encountered.')

        # debug
        # print('type: ' + str(msg_type))
        # print('body size: ' + str(body_size))
        # print('vhead size: ' + str(vhead_size))
        # print('vhead: ' + str(vhead))
        # print('sender: ' + sender_addr)
        # print('dest: ' + dest_addr)
        # print('payload: ' + str(payload))
        # print(type(payload))

        return (msg_type, sender_addr, dest_addr, payload)


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
