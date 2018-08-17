""" PTC Sim's collection of railroad component classes, including the track, 
    locomotives, base stations, etc., and their specific simulation threads.


    Author: Dustin Fast, 2018
"""

from time import sleep
from json import loads
from random import randint
from threading import Thread
from ConfigParser import RawConfigParser
from math import degrees, radians, sin, cos, atan2

from lib_app import Logger
from lib_msging import Connection, Queue, Message

# Init conf
config = RawConfigParser()
config.read('config.dat')

# Import conf data
REFRESH_TIME = int(config.get('application', 'refresh_time'))

TRACK_RAILS = config.get('track', 'track_rails')
TRACK_LOCOS = config.get('track', 'track_locos')
TRACK_BASES = config.get('track', 'track_bases')
SPEED_UNITS = config.get('track', 'speed_units')
TRACK_TIMEOUT = int(config.get('track', 'component_timeout'))

START_DIR = config.get('locomotive', 'start_direction')
START_MP = float(config.get('locomotive', 'start_milepost'))
START_SPEED = float(config.get('locomotive', 'start_speed'))

MSG_INTERVAL = int(config.get('messaging', 'msg_interval'))
BOS_EMP = config.get('messaging', 'bos_emp_addr')
LOCO_EMP_PREFIX = config.get('messaging', 'loco_emp_prefix')

# Track level logger
track_logger = Logger('log_track', True)


##################
# Parent Classes #
##################

class DeviceSim(object):
    """ A collectoin of threads representing a device simulation with a start
        and stop interface.
        Assumes each thread implements self.running (a bool) as a poison pill.
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
            print('* Stopped sim thread ' + self.label)
            self.running = False  # Thread poison pill
            [t.join(timeout=REFRESH_TIME) for t in self._threads]


class TrackDevice(object):
    """ The template class for on-track, communication-enabled devices. I.e., 
        Locos, Bases, and Waysides. Each devices contains a type-specific,
        real-time activity and communications simulation for testing and
        demonstration purposes.
    """
    def __init__(self, ID, track, device_type, milepost=None):
        """ self.ID         : (str) The Device's unique identifier
            self.track      : (Track) Track object reference
            self.milepost   : (Milepost) The devices location, as a Milepost
            self.conns      : (list) Connection objects
            self.sim        : The device's simulation. Start w/self.sim.start()
        """
        self.ID = ID
        self.name = device_type + ' ' + self.ID
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


#################
# Child Classes #
#################

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
        TrackDevice.__init__(self, str(ID), track, 'Loco')
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

        simlabel = 'Loco ' + self.ID
        self.sim = DeviceSim(simlabel, [self._sim])
        
        # Randomize speed, direction, etc., so everything is warm and fuzzy.
        self._randomize_attributes()

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

    def status_dict(self):
        """ Returns loco's current status as a dict of strings and nums.
        """
        return {'loco': self.ID,
                'speed': self.speed,
                'heading': self.heading,
                'direction': self.direction,
                'milepost': self.milepost.marker,
                'lat': self.milepost.lat,
                'long': self.milepost.long,
                'base': self.baseID,
                'bases': str([b.ID for b in self.bases_inrange])}

    def _randomize_attributes(self):
        """ Randomizes (within reason) speed, heading, direction, bpp, and mp.
        """
        self.speed = randint(0, 60)
        self.heading = randint(0, 359)
        self.direction = {0: 'increasing', 1: 'decreasing'}.get(randint(0, 1))
        self.bpp = randint(0, 90)

        if self.track.mileposts:
            max_index = len(self.track.mileposts) - 1
            self.milepost = self.track.mileposts.values()[randint(0, max_index)]

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
        
        while self.sim.running:
            # Sleep for specified interval
            sleep(MSG_INTERVAL)
            
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
                    err_str = self.name + '- At end of track. Reversing.'
                    track_logger.info(err_str)
                    self.direction *= -1
                else:
                    _set_heading(self.milepost, new_mp)
                    self.milepost = new_mp
                    self.makeup_dist = dist

                    # Determine base stations in range of current position
                    self.bases_inrange = [b for b in self.track.bases.values()
                                          if b.covers_milepost(self.milepost)]
                    
                    # Reset existing radio connections
                    for c in self.conns.values():
                        c.connected_to = None

                    # Assign in-range bases to loco radios, one base per radio
                    num_matches = min(len(self.bases_inrange), len(self.conns))
                    for i in range(num_matches - 1):
                        self.conns[i].connected_to = self.bases_inrange[i]

            # Build status msg to send to BOS
            msg_type = 6000
            msg_source = self.emp_addr
            msg_dest = BOS_EMP
            payload = str(self.status_dict())

            status_msg = Message((msg_type,
                                  msg_source,
                                  msg_dest,
                                  payload))

            # TODO: Locos need to establish a connection with one base and
            # maintain it while in range

            conns = [c for c in self.conns.values() if c.connected_to]

            if not conns:
                # TODO: Implement for all:
                err_str = 'Skipping msg send/recv - No connection available.'
                logger.warn(err_str)
                continue  # Note: we sleep at the top of this loop
            
            conn = conns[0]

            # Do status msg send
            try:
                conn.send(status_msg)
                track_logger.info(self.name + '-  Sent status msg.')
            except Exception as e:
                track_logger.error(self.name + ' - Msg send failed: ' + str(e))

            # Receive all incoming CAD message, if any
            while True:
                cad_msg = None
                try:
                    cad_msg = conn.fetch_next_msg(self.emp_addr)
                except Queue.Empty:
                    break  # Queue is empty
                except Exception as e:
                    # err_str = ' - Could not connect to broker.'
                    track_logger.warn(self.name + str(e))
                    break

                # Process cad msg, if msg and if actually for this loco
                if cad_msg and cad_msg.payload.get('ID') == self.ID:
                    try:
                        # TODO: Update track restrictions based on msg
                        track_logger.info(self.name + ' - CAD msg processed.')
                    except:
                        track_logger.error(
                            self.name + ' - Received invalid CAD msg.')


class Base(TrackDevice):
    """ An abstraction of a 220 MHz base station, including it's coverage area.
        Includes a realtime simulation of its activity/communications.
    """
    def __init__(self, ID, track, coverage_start, coverage_end):
        """ self.ID = (String) The base station's unique identifier
            self.coverage_start = (float) Coverage start milepost
            self.coverage_end = (float) Coverage end milepost
        """
        TrackDevice.__init__(self, ID, track, 'Base')
        self.cov_start = coverage_start
        self.cov_end = coverage_end

    def covers_milepost(self, milepost):
        """ Given a milepost, returns True if this base provides 
            coverage at that milepost, else returns False.
        """
        return milepost.marker >= self.cov_start and milepost.marker <= self.cov_end

    def _sim(self):
        """ Manages a connection to loco for reprorting locos connected """
        pass


class Wayside(TrackDevice):
    """ An abstraction of a wayside. Includes a realtime simulation of its 
        activity/communications.
    """

    def __init__(self, ID, track, milepost, children={}):
        """ self.ID      : (str) The waysides unique ID/address
            self.milepost: (Milepost) The waysides location as a Milepost
            self.children: (dict) Child devices { CHILD_ID: CHILD_OBJECT }
        """
        TrackDevice.__init__(self, ID, track, 'Wayside')
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

    def __init__(self, ID, track, milepost):
        """
        """
        TrackDevice.__init__(self, ID, track, 'Waychild')
        self.status = None

    def get_position(self):
        """ Returns a string represenation of the devices status.
        """
        raise NotImplementedError


#######################
# Independent Classes #
#######################


class Track(object):
    """ A representation of the track, including its mileposts and radio base 
        stations.
    
        self.locos = A dict of locootives.
            Format: { LOCOID: LOCO_OBJECT }
        self.bases = A dict of radio base stations, used by locos to send msgs. 
            Format: { BASEID: BASE_OBJECT }
        self.mileposts = A dict of all track mileposts
            Format: { MP: MP_OBJECT }
        self.marker_linear = A representation of the track in order of mps.
            Format: [ MP_1, ... , MP_n ], where MP1 < MPn
        self.marker_linear_rev = A represention the track in reverse order of mps.
            Format: [ MP_n, ... , MP_1], where MP1 < MPn
        Note: BASEID/LOCOD = strings, MP = floats
    """

    def __init__(self,
                 track_file=TRACK_RAILS,
                 locos_file=TRACK_LOCOS,
                 bases_file=TRACK_BASES):
        """ track_file: Track JSON representation
            locos_file: Locos JSON representation
            bases_file: Base stations JSON representation
        """
        self.locos = {}
        self.bases = {}
        self.mileposts = {}
        self.marker_linear = []
        self.marker_linear_rev = []
        # self.restrictions = {}  # { AUTH_ID: ( START_MILEPOST, END_MILEPOST }

        # Populate bases station (self.bases) from base_file
        try:
            with open(bases_file) as base_data:
                bases = loads(base_data.read())
        except Exception as e:
            raise Exception('Error reading ' + bases_file + ': ' + str(e))

        for base in bases:
            try:
                baseID = base['id']
                coverage_start = float(base['coverage'][0])
                coverage_end = float(base['coverage'][1])
            except ValueError:
                raise ValueError('Conversion error in ' + bases_file + '.')
            except KeyError:
                raise Exception('Malformed ' + bases_file + ': Key Error.')

            self.bases[baseID] = Base(
                baseID, self, coverage_start, coverage_end)

        # Populate milepost objects (self.mileposts) from track_file
        try:
            with open(track_file) as rail_data:
                mileposts = loads(rail_data.read())
        except Exception as e:
            raise Exception('Error reading ' + track_file + ': ' + str(e))

        for marker in mileposts:
            try:
                mp = float(marker['milemarker'])
                lat = float(marker['lat'])
                lng = float(marker['long'])
            except ValueError:
                raise ValueError('Conversion error in ' + track_file + '.')
            except KeyError:
                raise Exception('Malformed ' + track_file + ': Key Error.')

            self.mileposts[mp] = Milepost(mp, lat, lng)

        for mp in sorted(self.mileposts.keys()):
            self.marker_linear.append(mp)
        self.marker_linear_rev = self.marker_linear[::-1]

        # Populate Locomotive objects (self.locos) from locos_file
        try:
            with open(locos_file) as loco_data:
                locos = loads(loco_data.read())
        except Exception as e:
            raise Exception('Error reading ' + locos_file + ': ' + str(e))

        for loco in locos:
            try:
                self.locos[loco['id']] = Loco(loco['id'], self)
            except KeyError:
                raise Exception('Malformed ' + locos_file + ': Key Error.')

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
        mp = curr_mp.marker
        target_mp = mp + distance
        dist_diff = 0
        next_mp = None

        # Set the milepost object list to iterate, depending on direction
        if distance > 0:
            mps = self.marker_linear
        elif distance < 0:
            mps = self.marker_linear_rev

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
        return self.mileposts.get(mile, None)


class Milepost:
    """ An abstraction of a milepost.
    """
    def __init__(self, marker, latitude, longitude):
        """ self.marker = (float) The numeric milepost marker
            self.lat = (float) Latitude of milepost
            self.long = (float) Longitude of milepost
        """
        self.marker = marker
        self.lat = latitude
        self.long = longitude

    def __str__(self):
        """ Returns a string representation of the milepost.
         """
        return str(self.marker)
