""" PTC Sim's collection of railroad component classes, including the track, 
    locomotives, base stations, etc., and their specific simulation threads.


    Author: Dustin Fast, 2018
"""

import datetime
from time import sleep
from json import loads
from threading import Thread
from ConfigParser import RawConfigParser
from math import degrees, radians, sin, cos, atan2

from lib_app import Logger
from lib_msging import Client, Receiver, Queue, Message

# Init conf
config = RawConfigParser()
config.read('config.dat')

# Import conf data
REFRESH_TIME = int(config.get('application', 'refresh_time'))

TRACK_RAILS = config.get('track', 'track_rails')
TRACK_BASES = config.get('track', 'track_bases')
SPEED_UNITS = config.get('track', 'speed_units')
TRACK_TIMEOUT = int(config.get('track', 'component_timeout'))

START_DIR = config.get('locomotive', 'start_direction')
START_MP = float(config.get('locomotive', 'start_milepost'))
START_SPEED = float(config.get('locomotive', 'start_speed'))

MSG_INTERVAL = int(config.get('messaging', 'msg_interval'))
BOS_EMP = config.get('messaging', 'bos_emp_addr')
LOCO_EMP_PREFIX = config.get('messaging', 'loco_emp_prefix')

# Module level logger
g_logger = Logger('lib_track', True)


class Track(object):
    """ A representation of the track, including its mileposts and radio base 
        stations.
    
        self.locos = A dict of locootives.
            Format: { LOCOID: LOCO_OBJECT }
        self.bases = A dict of radio base stations, used by locos  to send msgs. 
            Format: { BASEID: BASE_OBJECT }
        self.mp_objects = Used to associate BRANCH/MP with MPOBJ.
            Format: { MP: MP_OBJECT }
        self.mp_linear = A representation of the track in order of mps.
            Format: [ MP_1, ... , MP_n ], where MP1 < MPn
        self.mp_linear_rev = A represention the track in reverse order of mps.
            Format: [ MP_n, ... , MP_1], where MP1 < MPn
        Note: BASEID/LOCOD = strings, MP = floats
    """

    def __init__(self, track_file=TRACK_RAILS, bases_file=TRACK_BASES):
        """ track_file: Filename of track JSON
            bases_file: Filename of base station JSON
        """
        self.locos = {}
        self.bases = {}
        self.mp_objects = {}
        self.mp_linear = []
        self.mp_linear_rev = []

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
                raise ValueError('Conversion error in ' + bases_file + '.')
            except KeyError:
                raise Exception('Missing key in ' + bases_file + '.')

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
                raise ValueError('Conversion error in ' + track_file + '.')
            except KeyError:
                raise Exception('Missing key in ' + track_file + '.')

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
            debug_str = '_get_next_mp failed to find a next milepost from: '
            debug_str += str(mps) + '\n'
            debug_str += 'cur_mp: ' + str(mp) + '\n'
            debug_str += 'moved : ' + str(distance) + '\n'
            debug_str += 'tgt_mp: ' + str(target_mp) + '\n'
            debug_str += 'mp_idx: ' + str(i) + '\n'
            debug_str += 'nxt_mp: ' + str(next_mp) + '\n'
            debug_str += 'disdif: ' + str(dist_diff) + '\n'
            raise Exception(debug_str)

        return next_mp_obj, dist_diff

    def get_milepost_at(self, mile):
        """ Returns the Milepost at distance (a float) iff one exists.
        """
        return self.mp_objects.get(mile, None)


class Connection(object):
    """ An abstraction of a communication interface. Ex: A 220 MHz radio
        connection. Contains a messaging client and a thread 
        that unsets self.active on timeout.
    """

    def __init__(self, ID, timeout=0):
        """ self.ID             : (str) The interfaces unique ID/address.
            self.last_activity  : (datetime) Time of last activity
            self.client         : (Client) The interfaces messaging client
            self.Receiver       : (Receiver) Incoming TCP/IP connection watcher
            self.connected_to   : (TrackDevice)            

            self._timeout_seconds: (int) Seconds of inactivity before timeout
            self._timeout_watcher: A thread. Updates self.active on timeout
        """
        # Properties
        self.ID = ID
        self.last_activity = None
        # self.transport_class = None

        # Interface
        self.client = Client()
        self.receiver = Receiver()

        # Timeout
        self._timeout = timeout
        self.timeout_watcher = Thread(target=self._timeoutwatcher)
        self.timeout_watcher.start()

    def __str__(self):
        """ Returns a string representation of the base station """
        ret_str = 'Connection' + self.ID + ': '
        ret_str += {True: 'Active', False: 'Inactive'}.get(self.active)

        return ret_str

    def send(self, message):
        """ Sends the given message over the connection's interface. Also
            updates keep alive.
        """
        self.client.send_msg(message)
        self.keep_alive()

    def fetch(self, queue_name):
        """ Fetches the next message from the given queue at the broker and
            returns it. Also updates keep alive.
        """
        self.client.fetch_next_msg(queue_name)
        self.keep_alive()

    def keep_alive(self):
        """ Update the last activity time to prevent timeout.
        """
        self.active = True
        self.last_activity = datetime.datetime.now()

    def _timeoutwatcher(self):
        """ Resets the connections 'active' flag if timeout elapses
            Intended to run as a thread.
        """
        while True:
            if not self.last_activity:
                self.connected_to = None
            elif self._timeout != 0:
                delta = datetime.timedelta(seconds=self._timeout)
                if delta < datetime.datetime.now() - self.last_activity:
                    self.connected_to = None

            sleep(REFRESH_TIME)


class TrackSim(object):
    """ Represents a device simulation.
    """
    def __init__(self, label, targets=[]):
        self.running = False  # Thread kill signal
        self._thread_targets = targets
        self._threads = []
        self.label = label
        
    def start(self):
        """ Starts the simulation threads. 
        """
        if not self.running:
            self.running = True
            self._threads = [Thread(target=t) for t in self._thread_targets]
            [t.start() for t in self._threads]

    def stop(self):
        """ Stops the simulation threads.
        """
        if self.running:
            self.running = False  # Signal kill to threads
            [t.join(timeout=REFRESH_TIME) for t in self._threads.values()]


class TrackDevice(object):
    """ The template class for on-track, communication-enabled devices. I.e., 
        Locos, Bases, and Waysides. Each devices contains a type-specific,
        real-time activity and communications simulation for testing and
        demonstration purposes.
    """

    def __init__(self, ID, milepost=None, track=None):
        """ self.ID         : (str) The Device's unique identifier
            self.track      : (Track) Track object reference
            self.milepost   : (Milepost) The devices location, as a Milepost
            self.conns      : (list) Connection objects
            self.sim        : The device's simulation. Start w/self.sim.start()
        """
        self.ID = ID
        self.track = track
        self.milepost = milepost
        self.conns = None
        self.sim = None

    def __str__(self):
        """ Returns a string representation of the device """
        return __name__ + ' ' + self.ID

    def add_connection(self, connection):
        """ Adds the given Connection instance to the devices's connections.
        """
        self.conns[connection.ID] = connection

    def is_online(self):
        """ Returns True iff at least one of the device's connections is active.
        """
        if [c for c in self.conns if c.active]:
            return True

    def _sim(self):
        """ Virtual function.
        """
        raise NotImplementedError


class Loco(TrackDevice):
    """ An abstration of a locomotive. Includes a realtime simulation of its 
        activity/communications.
    """
    def __init__(self, ID, track):
        """ self.ID         : (str) The Locomotives's unique identifier
            self.speed      : (float)
            self.heading    : (float)
            self.direction  : (str) Either 'increasing' or 'decreasing'
            self.milepost   : (Milepost) Current location, as a Milepost
            self.bpp        : (float) Brake pipe pressure. Affects braking.
            self.baseID     : (int)
            self.bases_inrange: (list) Base objects within communication range
        """
        TrackDevice.__init__(self, str(ID))
        self.speed = None
        self.heading = None
        self.direction = None
        self.milepost = None
        self.bpp = None

        self.baseID = None
        self.bases_inrange = []
        self.emp_addr = LOCO_EMP_PREFIX + self.ID

        self.conns = {'Radio1': Connection('Radio1', timeout=TRACK_TIMEOUT),
                      'Radio2': Connection('Radio2', timeout=TRACK_TIMEOUT)}

        self.sim = TrackSim(str(self), self._sim)

    def update(self,
               speed=None,
               heading=None,
               direction=None,
               milepost=None,
               bpp=None,
               baseID=None,
               bases_inrange=None):
        """ speed: A float
            heading: A float
            direction: Either 'increasing', or 'decreasing'
            milepost: A Milepost object instance
            bpp: A float
            baseID: An int
            bases_inrange: A list of Base object instances
        """
        if speed is not None:
            self.speed = speed
        if heading is not None:
            self.heading = heading
        if direction is not None:
            self.direction = direction
        if milepost is not None:
            self.milepost = milepost
        if bpp is not None:
            self.bpp = bpp
        if baseID is not None:
            self.baseID = baseID
        if self.bases_inrange is not None:
            self.bases_inrange = bases_inrange

    def get_status_dict(self):
        """ Returns loco's current status as a dict of strings and nums.
        """
        return {'loco': self.ID,
                'speed': self.speed,
                'heading': self.heading,
                'direction': self.direction,
                'milepost': self.milepost.mp,
                'lat': self.milepost.lat,
                'long': self.milepost.long,
                'base': self.baseID,
                'bases': str([b.ID for b in self.bases_inrange])}

    def _sim(self):
        """ Simulates the locomotive messaging systems and its movement along
            the track.
        """
        def _brake(self):
            """ Apply the adaptive braking algorithm.
            """
            raise NotImplementedError

        def _set_heading(prev_mp, curr_mp):
                """ Sets loco heading based on current and prev lat/long
                """
                lat1 = radians(prev_mp.lat)
                lat2 = radians(curr_mp.lat)

                long_diff = radians(prev_mp.long - curr_mp.long)

                a = cos(lat1) * sin(lat2)
                b = (sin(lat1) * cos(lat2) * cos(long_diff))
                x = sin(long_diff) * cos(lat2)
                y = a - b
                deg = degrees(atan2(x, y))
                compass_bearing = (deg + 360) % 360

                self.heading = compass_bearing 

        # Set location and movement params as needed
        self.makeup_dist = 0
        self.milepost = self.track.get_milepost_at(START_MP)
        if not self.milepost:
            raise ValueError('No milepost exists at the given start milepost')
        
        if not self.speed:
            self.speed = START_SPEED
        if not self.direction:
            self.direction = START_DIR
        
        while sim.running:
            # Move, if at speed
            if self.speed > 0:
                # Determine dist traveled since last iteration, including
                # makeup distance, if any.
                hours = REFRESH_TIME / 3600.0  # Seconds to hours, for mph
                dist = self.speed * hours * 1.0  # distance = speed * time
                dist += self.makeup_dist

                # Set sign of dist based on dir of travel
                if self.direction == 'decreasing':
                    dist *= -1

                # Get next milepost and any makeup distance
                new_mp, dist = self.track._get_next_mp(self.milepost, dist)
                if not new_mp:
                    g_logger.info(' End of track reached - Changing direction.')
                    self.direction *= -1
                else:
                    _set_heading(self.milepost, new_mp)
                    self.milepost = new_mp
                    self.makeup_dist = dist

                    # Determine base stations in range of current position
                    self.bases_inrange = [b for b in self.track.bases.values()
                                          if b.covers_milepost(self.milepost)]
                    
                    # Reset existing radio connections
                    for c in self.conns:
                        c.connected_to = None

                    # Assign in-range bases to loco radios, one base per radio
                    num_matches = max(len(self.bases_inrange), len(self.conns))
                    for i in range(num_matches):
                        self.conns[i].connected_to = self.bases_inrange[i]

            # Build status msg to send to BOS
            msg_type = 6000
            msg_source = self.emp_addr
            msg_dest = BOS_EMP
            payload = str(self.get_status_dict())

            status_msg = Message((msg_type,
                                  msg_source,
                                  msg_dest,
                                  payload))

            # Send status message over each active connection
            conns = [c for c in self.conns if c.connected_to]
            for conn in conns:
                try:
                    conn.send(status_msg)
                    g_logger.info(str(self) + '-  Sent status msg.')
                except Exception as e:
                    g_logger.error(str(self) + ' - Msg send failed: ' + str(e))

            # Receive and process all incoming CAD message, if any
            while True:
                cad_msg = None
                try:
                    cad_msg = conn.fetch_next_msg(self.emp_addr)
                except Queue.Empty:
                    break  # Queue empty / all msgs fetched
                except Exception as e:
                    g_logger.error(str(self) + ' - Fetch connection error.')

                # Process cad msg if msg is actually for this loco
                if cad_msg.payload.get('ID') == self.ID:
                    try:
                        # TODO: Update track restrictions
                        g_logger.info(str(self) + ' - CAD msg processed.')
                    except:
                        g_logger.error(str(self) + ' - Received invalid CAD msg.')

                sleep(MSG_INTERVAL)


class Base(TrackDevice):
    """ An abstraction of a 220 MHz base station, including it's coverage area.
        Includes a realtime simulation of its activity/communications.
    """
    def __init__(self, ID, coverage_start, coverage_end):
        """ self.ID = (String) The base station's unique identifier
            self.coverage_start = (float) Coverage start milepost
            self.coverage_end = (float) Coverage end milepost
        """
        TrackDevice.__init__(self, ID)
        self.cov_start = coverage_start
        self.cov_end = coverage_end

    def covers_milepost(self, milepost):
        """ Given a milepost, returns True if this base provides 
            coverage at that milepost, else returns False.
        """
        return milepost.mp >= self.cov_start and milepost.mp <= self.cov_end


class Wayside(TrackDevice):
    """ An abstraction of a wayside. Includes a realtime simulation of its 
        activity/communications.
    """

    def __init__(self, ID, milepost, children={}):
        """ self.ID      : (str) The waysides unique ID/address
            self.milepost: (Milepost) The waysides location as a Milepost
            self.children: (dict) Child devices { CHILD_ID: CHILD_OBJECT }
        """
        TrackDevice.__init__(self, ID)
        self.children = {}

    def add_child(self, child_object):
        """ Given a child object (i.e. a switch), adds it to the wayside as a 
            device.
        """
        self.children[child_object.ID] = child_object


class WayChild(TrackDevice):
    """ An abstraction of a wayside child device. Ex: A Switch.
        Includes a realtime simulation of its activity/communications.
    """

    def __init__(self, ID, type):
        """
        """
        self.ID = ID
        self.status = None

    def get_position(self):
        """ Returns a string represenation of the devices status.
        """
        raise NotImplementedError


class Milepost:
    """ An abstraction of a milepost.
    """
    def __init__(self, mp, latitude, longitude):
        """ self.mp = (float) The numeric milepost marker
            self.lat = (float) Latitude of milepost
            self.long = (float) Longitude of milepost
        """
        self.mp = mp
        self.lat = latitude
        self.long = longitude

    def __str__(self):
        """ Returns a string representation of the milepost.
         """
        return str(self.mp)
    
if __name__ == '__main__':
    l = Loco('t', None)
    l.sim.start()
