""" PTCSim's collection of railroad component classes, including the track, 
    locomotives, base stations, etc., and their specific simulation threads.


    Author: Dustin Fast, 2018
"""

import datetime
from time import sleep
from json import loads
from threading import Thread
from ConfigParser import RawConfigParser

from lib_msging import Client, Receiver

# Init conf
config = RawConfigParser()
config.read('config.dat')

# Import conf data
REFRESH_TIME = int(config.get('application', 'refresh_time'))
TRACK_RAILS = config.get('track', 'track_rails')
TRACK_BASES = config.get('track', 'track_bases')
SPEED_UNITS = config.get('track', 'speed_units')
CONN_TIMEOUT = config.get('track', 'component_timeout')


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

    def __init__(self, ID, enabled=True, timeout=0):
        """ self.ID             : (str) The interfaces unique ID/address.
            self.enabled        : (bool) Denotes connection is enabled
            self.active         : (bool) Denotes connection is active
            self.last_activity  : (datetime) Time of last activity
            self.client         : (Client) The interfaces messaging client
            self.Receiver       : (Receiver) Incoming TCP/IP connection watcher

            self._timeout_seconds: (int) Seconds of inactivity before timeout
            self._timeout_watcher: A thread. Updates self.active on timeout
        """
        # Properties
        self.ID = ID
        self.enabled = enabled
        self.active = None
        self.last_activity = None

        # Interface
        self.client = Client()
        self.receiver = Receiver()

        # Timeout
        self.set_timeout(timeout)
        self.timeout_watcher = Thread(target=self._timeoutwatcher)

    def __str__(self):
        """ Returns a string representation of the base station """
        ret_str = 'Connection' + self.ID + ': '
        ret_str += {True: 'Enabled', False: 'Disabled'}.get(self.enabled)
        ret_str += {True: 'Active', False: 'Inactive'}.get(self.active)

        return ret_str

    def send(self, payload):
        """ Sends the given payload over the connection's interface. Also
            updates keep alive.
        """
        # TODO: send payload over client
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
            delta = datetime.timedelta(seconds=self._timeout_seconds)
            if delta < datetime.datetime.now() - self.last_activity:
                self.active = False

            sleep(REFRESH_TIME)

    def set_timeout(self, timeout):
        """ Sets the timeout value and starts/stops the timeout watcher thread
            as needed. 0 = No timeout.
        """
        self._timeout_seconds = timeout
        if self._timeout_seconds:
            if not self.timeout_watcher.is_alive():
                self.timeout_watcher = Thread(target=self._timeoutwatcher)
                self.timeout_watcher.start()
        else:
            if self.timeout_watcher.is_alive():
                self.timeout_watcher.terminate()
                self.timeout_watcher.join()  # To prevent temporary offline


class TrackComponent(object):
    """ The template class for on-track, communication-enabled devices. I.e., 
        Locos, Bases, and Waysides. Each component contains a type-specific,
        real-time activity and communications simulation for testing and
        demonstration purposes.
    """

    def __init__(self, ID, milepost=None, enabled=True, connections={}):
        """ self.ID         : (str) The Device's unique identifier.
            self.milepost   : (Milepost) The devices location, as a Milepost
            self.conns      : (list) Connection objects: { ID_STR: Connection }
            self.sim        : The component simulation. Start w/self.sim.start()
        """
        self.ID = ID
        self.milepost = milepost
        self.enabled = enabled
        self.conns = connections

        self._sim_running = False

    def __str__(self):
        """ Returns a string representation of the component """
        return __name__ + ' ' + self.ID

    def add_connection(self, connection):
        """ Adds the given Connection instance to the component's connections.
        """
        self.conns[connection.ID] = connection

    def startsim(self):
        """ Starts a simulation of the component, if defined.
        """
        if not self._sim_running:
            self._sim_running = True
            self.sim = Thread(target=self._sim)
            self.sim.start()
            # TODO: Logger

    def stopsim(self):
        """
        """
        if self._sim_running:
            self._sim_running = False
            self.sim.join()
            # TODO: Logger

    def is_online(self):
        """ Returns True iff at least one of the device's connections is active.
        """
        if [c for c in self.conns if c.active]:
            return True

    def _sim(self):
        """
        """
        raise NotImplementedError


class Loco(TrackComponent):
    """ An abstration of a locomotive. Includes a realtime simulation of its 
        activity/communications.
    """

    def __init__(self, ID):
        """ self.ID         : (str) The Locomotives's unique identifier
            self.speed      : (float)
            self.heading    : (float)
            self.direction  : (str) Either 'increasing' or 'decreasing'
            self.milepost   : (Milepost) Current location, as a Milepost
            self.bpp        : (float) Brake pipe pressure. Affects braking.
            self.baseID     : (int)
            self.bases_inrange: (list) Base objects within communication range
        """
        TrackComponent.__init__(self, str(ID))
        self.speed = None
        self.heading = None
        self.direction = None
        self.milepost = None
        self.bpp = None
        self.baseID = None
        self.bases_inrange = []

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

    def _brake(self):
        """ # TODO Apply the adaptive braking algorithm.
        """
        raise NotImplementedError

    def _sim(self):
        """
        """
        raise NotImplementedError


class Base(TrackComponent):
    """ An abstraction of a 220 MHz base station, including it's coverage area.
        Includes a realtime simulation of its activity/communications.
    """

    def __init__(self, ID, coverage_start, coverage_end):
        """ self.ID = (String) The base station's unique identifier
            self.coverage_start = (float) Coverage start milepost
            self.coverage_end = (float) Coverage end milepost
        """
        TrackComponent.__init__(self, ID)
        self.cov_start = coverage_start
        self.cov_end = coverage_end
        self.sim = None

    def covers_milepost(self, milepost):
        """ Given a milepost, returns True if this base provides 
            coverage at that milepost, else returns False.
        """
        return milepost.mp >= self.cov_start and milepost.mp <= self.cov_end

    def _sim(self):
        """
        """
        raise NotImplementedError


class Wayside(TrackComponent):
    """ An abstraction of a wayside. Includes a realtime simulation of its 
        activity/communications.
    """

    def __init__(self, ID, milepost, children={}):
        """ self.ID      : (str) The waysides unique ID/address
            self.milepost: (Milepost) The waysides location as a Milepost
            self.children: (dict) Child devices { CHILD_ID: CHILD_OBJECT }
        """
        TrackComponent.__init__(self, ID)
        self.children = {}
        self.sim = None

    def add_child(self, child_object):
        """ Given a child object (i.e. a switch), adds it to the wayside as a 
            device.
        """
        self.children[child_object.ID] = child_object

    def _sim(self):
        """
        """
        raise NotImplementedError


class WayChild(TrackComponent):
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

    def _sim(self):
        """
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


class Simulator(object):
    """ A templace Simulation class.
    """
