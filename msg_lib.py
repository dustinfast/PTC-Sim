""" A messaging library for sending and receiving fixed-format, variable-
    length-header messages according to the Edge Message Protocol (EMP) 
    specification as defined in msg_spec/S-9354.pdf. See README.md for 
    implementation specific information.

    Contains classes that support message sending, watching, and receving.


    Author:
        Dustin Fast, 2018
"""

import struct
import binascii

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

        return raw_msg

    @staticmethod
    def _to_tuple(raw_msg):
        """ Returns a tuple representation of the msg contained in raw_msg.
        """
        # Validate raw_msg
        if not raw_msg or len(raw_msg) >= 20:  # 20 byte min msg size
            print('raw: "' + raw_msg + '"')  # debug
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
        # print('type: ' + str(msg_type))
        # print('body size: ' + str(body_size))
        # print('vhead size: ' + str(vhead_size))
        # print('vhead: ' + str(vhead))
        # print('sender: ' + sender_addr)
        # print('dest: ' + dest_addr)
        # print('payload: ' + str(payload))
        # print(type(payload))

        return (msg_type, sender_addr, dest_addr, payload)


class MsgWatcher(object):
    """ The message watcher. Monitors the given broker for messages in the
        queue specified.
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
        """
        assert(False)

    def close(self):
        """ Closes the connection to the broker.
        """
        assert(False)

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
        assert(False)

    def close(self):
        """ Closes the connection with the broker.
        """
        assert(False)

    def send_msg(self, message):
        """ Sends the given message over TCP/IP to the broker specified. At
            the broker, the msg is enqueued in the queue specified in the msg. 
        """
        assert(False)
