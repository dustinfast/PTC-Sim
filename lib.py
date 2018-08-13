""" lib.py - A collection of shared classes for loco_sim.
    Contains railroad components, input/output handlers, & messaging subsystem.
    See each section's docstring for more info, as well as README.md.

    Author: Dustin Fast, 2018
"""

#############################################################
# Library Initialization                                    #
#############################################################

# Init conf
from ConfigParser import RawConfigParser
config = RawConfigParser()
config.read('conf.dat')

# Railroad imports and conf data
from json import loads
TRACK_RAILS = config.get('track', 'track_rails')
TRACK_BASES = config.get('track', 'track_bases')

# Messaging imports and conf data
import struct
import socket
import binascii
from Queue import Empty

BROKER = config.get('messaging', 'broker')
SEND_PORT = int(config.get('messaging', 'send_port'))
FETCH_PORT = int(config.get('messaging', 'fetch_port'))
MAX_MSG_SIZE = int(config.get('messaging', 'max_msg_size'))
NET_TIMEOUT = float(config.get('messaging', 'network_timeout'))

# Input/Output imports and conf data
import logging
from logging.handlers import RotatingFileHandler as RFHandler

LOG_NAME = config.get('logging', 'filename')
LOG_LEVEL = int(config.get('logging', 'level'))
LOG_FILES = config.get('logging', 'num_logfiles')
LOG_SIZE = int(config.get('logging', 'max_logfile_size'))

# Decalare global logger (defined at eof)
logger = None


#############################################################
# Railroad/Locomotive Component Classes                     #
#############################################################
""" LocoSim's collection of railroad related classes, includes 
    the track, mileposts, locomotives, and base stations.
"""

class Track(object):
    """ A representation of the track, including its mileposts and radio base 
        stations.
    
        self.bases = A dict of radio base stations, used by locos  to send msgs. 
            Format: { BASEID: BASE_OBJECT }
        self.mp_objects = Used to associate BRANCH/MP with MPOBJ.
            Format: { MP: MPOBJ }
        self.mp_linear = A representation of the track in order of mps.
            Format: [ MP1, ... , MPn ], where MP1 < MPn
        self.mp_linear_rev = A represention the track in reverse order of mps.
            Format: [ MPn, ... , MP1], where MP1 < MPn
        Note: BASEID = string, MP/lat/long = floats, MPOBJs = Milepost objects.
    """
    def __init__(self, track_file=TRACK_RAILS, bases_file=TRACK_BASES):
        self.bases = {}
        self.mp_objects = {}
        self.mp_linear = []
        self.mp_linear_rev = []

        logger.info('Initializing Track...')

        # Populate bases station (self.bases) from base_file json
        try:
            with open(bases_file) as base_data:
                bases = loads(base_data.read())
        except Exception as e:
            raise Exception('Error reading ' + bases_file + ': ' + str(e))

        for b in bases:
            try:
                baseID = b['id']
                coverage_start = float(b['coverage'][0])
                coverage_end = float(b['coverage'][1])
            except ValueError:
                logger.warning('Discarded base "' + baseID + '": Conversion Error')
                continue
            except KeyError:
                raise Exception('Invalid data in ' + bases_file + '.')

            self.bases[baseID] = Base(baseID, coverage_start, coverage_end)

        # Populate milepost objects (self.mp_objects) from track_file json
        try:
            with open(TRACK_RAILS) as rail_data:
                mileposts = loads(rail_data.read())
        except Exception as e:
            raise Exception('Error reading ' + TRACK_RAILS + ': ' + str(e))

        # Build self.mp_objects dict
        for m in mileposts:
            try:
                mp = float(m['milemarker'])
                lat = float(m['lat'])
                lng = float(m['long'])
            except ValueError:
                logger.warning("Discarding mp '" + str(mp) + "': Conversion Error")
                continue
            except KeyError:
                raise Exception('Invalid data in ' + track_file + '.')

            self.mp_objects[mp] = Milepost(mp, lat, lng)

        # Populate self.mp_linear and self.mp_linear_rev from self.mp_objects
        for mp in sorted(self.mp_objects.keys()):
            self.mp_linear.append(mp)
        self.mp_linear_rev = self.mp_linear[::-1]

    def _get_next_mp(self, curr_mp, distance):
        """ Given a curr_mp and distance, returns the nearest mp marker at
            curr_mp + distance. Also returns any difference not accounted
            for.
            Accepts:
                curr_mp  = Curr location (a Milepost)
                distance = Distance in miles (neg dist denotes decreasing DOT)
            Returns:
                next_mp   = nearest mp for curr_mp + distance without going over
                dist_diff = difference between next_mp and actual location
            Note: If next_mp = curr_mp, diff = distance.
                  If no next mp (end of track), returns None.
        """
        # If no distance, next_mp is curr_mp
        if distance == 0:
            return curr_mp, distance

        # Working vars
        mp = curr_mp.mp
        target_mp = mp + distance
        dist_diff = 0
        next_mp = None

        # Set the milepost object list to iterate, depending on direction
        if distance > 0:
            mps = self.mp_linear
        elif distance < 0:
            mps = self.mp_linear_rev

        # Find next mp marker, noting unconsumed distance
        for i, marker in enumerate(mps):
            if marker == target_mp:
                next_mp = marker
                dist_diff = 0
                break
            elif (distance > 0 and marker > target_mp) or \
                 (distance < 0 and marker < target_mp):
                next_mp = mp
                if i > 0:
                    next_mp = mps[i - 1]
                dist_diff = abs(target_mp - next_mp)
                break

        # If we didn't find a next mp (i.e. end of track)
        if not next_mp:
            return

        # Get mp object associated with next_mp
        next_mp_obj = self.get_milepost_at(next_mp)
        if not next_mp_obj:
            # Print debug info
            log_str = '_get_next_mp failed to find a next milepost from: '
            log_str += str(mps) + ', '
            log_str += 'cur_mp: ' + str(mp) + ', '
            log_str += 'moved : ' + str(distance) + ', '
            log_str += 'tgt_mp: ' + str(target_mp) + ', '
            log_str += 'mp_idx: ' + str(i) + ', '
            log_str += 'nxt_mp: ' + str(next_mp) + ', '
            log_str += 'disdif: ' + str(dist_diff) + '.'
            logger.error(log_str) 
            raise Exception(log_str)

        return next_mp_obj, dist_diff

    def get_milepost_at(self, mile):
        """ Returns the Milepost at distance (a float) iff one exists.
        """
        return self.mp_objects.get(mile, None)


class Loco(object):
    """ An abstration of a locomotive.
    """
    def __init__(self, locoID, status_msg=None):
        """
        """
        self.ID = str(locoID)
        self.speed = None
        self.heading = None
        self.direction = None
        self.milepost = None
        self.current_base = None
        self.bases_inrange = []

        if status_msg:
            self.update_from_msg(status_msg)

    def update_from_msg(self, msg):
        """ Updates the loco with parameters from the given Message object.
            Assumes msg.payload is well-formed 6001 msg data.
        """
        content = msg.payload
        # print(type(content['loco']))

        # try:
        #     msg_locoID = content['loco']
        #     if content['loco'] != self.ID:
        #         warn_str = 'Updated loco ' + self.ID
        #         warn_str += ' from a msg for loco ' + msg_locoID
        #         logger.warning(warn_str)
        #     self.speed = content['speed']
        #     self.heading = content['heading']
        #     self.direction = content['direction']
        #     self.current_base = content['base']
        # except KeyError:
        #     raise Exception('Attempted loco update from a malformed message')

    def get_status(self):
        """ Returns a string representation of the locos current status.
        """
        # TODO: Combine with sim_loco.status
        if not self.bases_inrange:
            bases = 'no bases.'
        else:
            bases = 'bases ' + ', '.join(self.bases_inrange)
            bases += ' and connected to base ' + str(self.current_base) + '.'

        ret_str = 'Loco ' + self.ID
        ret_str += ' at mp ' + str(self.milepost)
        ret_str += ' traveling in a(n) ' + str(self.direction)
        ret_str += ' going ' + str(self.speed) + 'mph'
        ret_str += ' is in range of ' + bases
        return ret_str


class Milepost:
    """ An abstraction of a milepost.
        self.mp = (Float) The numeric milepost
        self.lat = (Float) Latitude of milepost
        self.long = (Float) Longitude of milepost
    """
    def __init__(self, mp, latitude, longitude):
        self.mp = mp
        self.lat = latitude
        self.long = longitude

    def __str__(self):
        """ Returns a string representation of the milepost """
        return str(self.mp)


class Base:
    """ An abstraction of a base station, including it's coverage area
        self.ID = (String) The base station's unique identifier
        self.coverage_start = (Float) Coverage start milepost
        self.coverage_end = (Float) Coverage end milepost
    """
    def __init__(self, baseID, coverage_start, coverage_end):
        self.ID = baseID
        self.cov_start = coverage_start
        self.cov_end = coverage_end

    def __str__(self):
        """ Returns a string representation of the base station """
        return self.ID

    def covers_milepost(self, milepost):
        """ Given a milepost, returns True if this base station provides 
            coverage at that milepost, else returns False.
        """
        return milepost.mp >= self.cov_start and milepost.mp <= self.cov_end


#############################################################
# Messaging Subsystem                                       #
#############################################################
""" LocoSim's messaging library for sending and receiving fixed-format, 
    variable-length header messages adhering to the Edge Message Protocol(EMP)
    over TCP/IP. See README.md for implementation specific information.
"""
# Set the timeout for all socket connections
socket.setdefaulttimeout(NET_TIMEOUT)
# TODO: Ensure this is set in each init where it's necessary for proper operation

class MsgQueue:
    """ A threadsafe message queue with push, pop, front, remove, is_empty, 
        and item_count methods. 
    """
    def __init__(self):
        self._items = []            # Container
        self.lock = False   # TODO: Threadsafe lock
        # TODO: Empty exception member

    def push(self, item):
        """ Adds an item to the back of queue.
        """
        self._items.append(item)

    def pop(self):
        """ Pops front item from queue and returns it.
            Raises Queue.Empty if is_empty on pop.
        """
        if self.is_empty():
            raise Empty
        d = self._items[0]
        self._items = self._items[1:]
        return d

    def front(self):
        """ Returns the item at the queue front, leaving queue unchanged.
            Raises Queue.Empty if queue empty.
        """
        if self.is_empty():
            raise Empty
        return self._items[0]

    def is_empty(self):
        """ Returns true iff queue empty.
        """
        return self.item_count() == 0

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
            # 8 bit variable header size
            raw_msg += struct.pack(">B", var_headsize)
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
        if not raw_msg or len(raw_msg) < 20:  # 20 byte min msg size
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
        try:
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
                raise Exception('Msg send failed: Broker responded with FAIL.')
            else:
                raise Exception(
                    'Unhandled response received from broker - Send aborted.')
        except Exception as e:
            raise Exception('Msg send failed: ' + str(e))

    def fetch_next_msg(self, queue_name):
        """ Fetches the next msg from queue_name from the broker and returns it,
            Raises Queue.Empty if specified queue is empty.
        """
        try:
            # Establish socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.broker, self.fetch_port))

            # Send queue name and wait for response
            sock.send(queue_name.encode())
            resp = sock.recv(MAX_MSG_SIZE)
        except Exception as e:
            raise Exception(e)

        msg = None
        if resp == 'EMPTY':
            raise Empty  # No msg available to fetch
        else:
            msg = Message(resp.decode('hex'))  # Response is the msg

        sock.close()

        return msg


#############################################################
# Input/Output Handlers (REPL, Logger, and Web)             #
#############################################################
""" LocoSim's input and output library - I.e., the read-eval-print-loop,
    log file writer, and web command handlers.
"""

class REPL(object):
    """ A dynamic Read-Eval-Print-Loop. I.e. A command line interface.
        Contains two predefined commands: help, and exit. Additional cmds may
        be added with add_cmd(). These additional cmds all operate on the object
        given as the context. 
        Note: Assumes all expressions provided are well-formed. 
    """

    def __init__(self, context, prompt='>>', welcome_msg=None):
        """ Instantiates an REPL object.
            context: The object all commands operate on.
            prompt: The REPL prompt.
            welcome: String to display on REPL start.
        """
        self.context = context
        self.prompt = prompt
        self.welcome_msg = welcome_msg
        self.exit_command = None
        self.commands = {'help': 'self._help()',
                         'exit': 'self._exit()'}

    def start(self):
        """ Starts the REPL.
        """
        if self.welcome_msg:
            print(self.welcome_msg)
        while True:
            # TODO: readline
            uinput = raw_input(self.prompt)
            cmd = self.commands.get(uinput)

            # Process user input
            if not uinput:
                continue  # if null input
            if not cmd:
                print('Invalid command. Try "help".')
            else:
                eval(cmd)

    def add_cmd(self, cmd_txt, expression):
        """ Makes a command available via the REPL
                cmd_txt: Txt cmd entered by the user
                expression: A well-formed python expression string.
                            ex: 'print('Hello World)'
        """
        if cmd_txt == 'help' or cmd_txt == 'exit':
            raise ValueError('An internal cmd override was attempted.')
        self.commands[cmd_txt] = 'self.context.' + expression

    def set_exitcmd(self, cmd):
        """ Specifies a command to run on exit. Example: 'stop', if a stop
            command is defined and performs cleanup, etc.
        """
        self.exit_command = cmd

    def _help(self):
        """ Outputs all available commands to the console, excluding 'help'.
        """
        cmds = [c for c in sorted(self.commands.keys()) if c != 'help']
        print('\n'.join(cmds))

    def _exit(self):
        """ Calls exit() after doing self.exit_command (if defined).
        """
        if self.exit_command:
            eval(self.commands[self.exit_command])
        exit()


class Logger(object):  
    # TODO: Inherit from logging.logger?
    """ A wrapper for Python's logging module. Implements a log with console
        output and rotating log files.
        Example usage: RotatingLog.error('Invalid Value!')
                       RotatingLog.info('Started Succesfully.')
    """
    def __init__(self, 
                 filename=LOG_NAME,
                 level=LOG_LEVEL,
                 num_files=LOG_FILES,
                 max_filesize=LOG_SIZE):
        """
        """
        self.logger = logging.getLogger()

        # Define log output format
        console_fmt = '%(asctime)s - %(levelname)s: %(message)s'
        log_fmt = '%(asctime)s - %(levelname)s @ %(module)s: %(message)s'
        console_fmt = logging.Formatter(console_fmt)
        log_fmt = logging.Formatter(log_fmt + '')

        # Init Console handler (stmnts go to console in addition to logfile)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(console_fmt)

        # Init log file rotation
        rotate_handler = RFHandler(filename, 
                                   max_filesize,
                                   num_files)  
        rotate_handler.setLevel(level)
        rotate_handler.setFormatter(log_fmt)

        # Init the logger itself
        self.logger.setLevel(0)
        self.logger.addHandler(rotate_handler)
        self.logger.addHandler(console_handler)


# Init global logger
logger = Logger().logger
