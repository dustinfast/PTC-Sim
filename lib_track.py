""" PTC-Sim's collection of railroad component classes, including the track, 
    locomotives, base stations, etc., and their specific simulation threads.


    Author: Dustin Fast, 2018
"""

from time import sleep
from json import loads
from random import randint
from threading import Thread
from ConfigParser import RawConfigParser
from math import degrees, radians, sin, cos, atan2

from lib_app import track_log
from lib_msging import Connection, Queue, get_6000_msg

# Init conf
config = RawConfigParser()
config.read('config.dat')

# Import conf data
REFRESH_TIME = int(config.get('application', 'refresh_time'))

TRACK_RAILS = config.get('track', 'track_rails')
TRACK_LOCOS = config.get('track', 'track_locos')
TRACK_BASES = config.get('track', 'track_bases')
SPEED_UNITS = config.get('track', 'speed_units')
CONN_TIMEOUT = int(config.get('track', 'component_timeout'))

MSG_INTERVAL = int(config.get('messaging', 'msg_interval'))
LOCO_EMP_PREFIX = config.get('messaging', 'loco_emp_prefix')


##################
# Parent Classes #
##################

class DeviceSim(object):
    """ A collection of threads representing a device simulation. Exposes start
        and stop interfaces.
        Assumes each thread implements self.running (a bool) as a poison pill.
    """
    def __init__(self, device, targets=[]):
        self.running = False  # Thread kill signal
        self._thread_targets = targets
        self._threads = []
        self.device = device
        self.label = device.name
        
    def start(self):
        """ Starts the simulation threads. 
        """
        if not self.running:
            self.running = True
            self._threads = [Thread(target=t, args=[self.device]) 
                             for t in self._thread_targets]
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
    def __init__(self, ID, device_type, milepost=None):
        """ self.ID         : (str) The Device's unique identifier
            self.milepost   : (Milepost) The devices location, as a Milepost
            self.conns      : (dict) Connection objects - { ID: Connection }
            self.sim        : The device's simulation. Start w/self.sim.start()
        """
        self.ID = ID
        self.name = device_type + ' ' + self.ID
        self.milepost = milepost
        self.conns = {}
        self.sim = None

    def __str__(self):
        """ Returns a string representation of the device """
        return self.name
        
    def add_connection(self, connection):
        """ Adds the given Connection instance to the devices's connections.
        """
        self.conns[connection.ID] = connection

    def is_online(self):
        """ Returns True iff at least one of the device's connections is active.
        """
        if [c for c in self.conns if c.active]:
            return True


#################
# Child Classes #
#################

class Loco(TrackDevice):
    """ An abstration of a locomotive. Includes a realtime simulation of its 
        activity/communications.
    """
    def __init__(self, ID, track):
        """ self.ID         : (str) The Locomotives's unique identifier
            self.track      : (Track) Track object ref
            self.speed      : (float) Current speed
            self.heading    : (float) Current compass bearing
            self.direction  : (str) Either 'increasing' or 'decreasing'
            self.milepost   : (Milepost) Current location, as a Milepost
            self.bpp        : (float) Brake pipe pressure. Affects braking.
            self.bases_inrange: (list) Base objects within communication range
        """
        TrackDevice.__init__(self, str(ID), 'Loco')
        self.emp_addr = LOCO_EMP_PREFIX + self.ID
        self.track = track

        self.speed = None
        self.heading = None
        self.direction = None
        self.milepost = None
        self.bpp = None
        self.bases_inrange = []
        self.bases = []

        self.conns = {'Radio1': Connection('Radio1', timeout=CONN_TIMEOUT),
                      'Radio2': Connection('Radio2', timeout=CONN_TIMEOUT)}

        self.sim = DeviceSim(self, [loco_movement, loco_messaging])
        
        # Randomize (within reason) speed, heading, direction, bpp, and mp.
        # TODO: Get these from last known postion
        self.speed = randint(0, 60)
        self.heading = randint(0, 359)
        self.direction = {0: 'increasing', 1: 'decreasing'}.get(randint(0, 1))
        self.bpp = randint(0, 90)

        if track.mileposts:
            max_index = len(track.mileposts) - 1
            self.milepost = track.mileposts.values()[
                randint(0, max_index)]

    def update(self,
               speed=None,
               heading=None,
               direction=None,
               milepost=None,
               bpp=None,
               bases=None):
        """ speed: A float, locos current speed.
            heading: A float, locos current compass bearing.
            direction: Either 'increasing', or 'decreasing'.
            milepost: A Milepost denoting Locos current location.
            bpp: A float, denoting current brake pipe pressure.
            bases: A dict denoting current base connections. Is of the 
                   format: { ConnectionLabel: base_ID }
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
        if bases is not None:
            if not bases:
                [c.disconnect for c in self.conns]
                return
            try:
                for conn_label, base_id in bases.iteritems():
                    self.conns[conn_label].connect(self.track.bases[base_id])
            except KeyError:
                err_str = ' - Invalid connection or base ID in bases param.'
                raise ValueError(self.name + err_str)


class Base(TrackDevice):
    """ An abstraction of a 220 MHz base station, including it's coverage area.
        Includes a realtime simulation of its activity/communications.
    """
    def __init__(self, ID, coverage_start, coverage_end):
        """ self.ID = (String) The base station's unique identifier
            self.coverage_start = (float) Coverage start milepost
            self.coverage_end = (float) Coverage end milepost
        """
        TrackDevice.__init__(self, ID, 'Base')
        self.cov_start = coverage_start
        self.cov_end = coverage_end

    def covers_milepost(self, milepost):
        """ Given a milepost, returns True if this base provides 
            coverage at that milepost, else returns False.
        """
        return milepost.marker >= self.cov_start and milepost.marker <= self.cov_end


class Wayside(TrackDevice):
    """ An abstraction of a wayside. Includes a realtime simulation of its 
        activity/communications.
    """

    def __init__(self, ID, milepost, children={}):
        """ self.ID      : (str) The waysides unique ID/address
            self.milepost: (Milepost) The waysides location as a Milepost
            self.children: (dict) Child devices { CHILD_ID: CHILD_OBJECT }
        """
        raise NotImplementedError
        # TrackDevice.__init__(self, ID, 'Wayside')
        # self.children = {}

    def add_child(self, child_object):
        """ Given a child object (i.e. a switch), adds it to the wayside as a 
            device.
        """
        raise NotImplementedError
        # self.children[child_object.ID] = child_object


class TrackSwitch(TrackDevice):
    """ An abstraction of an on-track directional switch.
        Includes a realtime simulation of its activity/communications.
    """

    def __init__(self, ID, milepost):
        """
        """
        raise NotImplementedError
        # TrackDevice.__init__(self, ID, 'Switch')
        # self.status = None

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
                base_id = str(base['id'])
                coverage_start = float(base['coverage'][0])
                coverage_end = float(base['coverage'][1])
            except ValueError:
                raise ValueError('Conversion error in ' + bases_file + '.')
            except KeyError:
                raise Exception('Malformed ' + bases_file + ': Key Error.')

            self.bases[base_id] = Base(base_id, coverage_start, coverage_end)

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
                loco_id = str(loco['id'])
                self.locos[loco_id] = Loco(loco_id, self)
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


##############################
# Track Device Sim Functions #
##############################

def loco_movement(loco):
    """ Real-time simulation of a locomotive's on-track movement. Also
        determines base stations in range of locos current position.
    """
    def _brake():
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

            loco.heading = compass_bearing

    # Start of locomotive simulator
    makeup_dist = 0
    if not loco.direction or not loco.milepost or loco.speed is None:
        raise ValueError('Cannot simulate an unintialized Locomotive.')

    while loco.sim.running:
        sleep(MSG_INTERVAL)  # Sleep for specified interval

        # Move, if at speed
        if loco.speed > 0:
            # Determine dist traveled since last iteration, including
            # makeup distance, if any.
            hours = REFRESH_TIME / 3600.0  # Seconds to hours, for mph
            dist = loco.speed * hours * 1.0  # distance = speed * time
            dist += makeup_dist

            # Set sign of dist based on dir of travel
            if loco.direction == 'decreasing':
                dist *= -1

            # Get next milepost and any makeup distance
            new_mp, dist = loco.track._get_next_mp(loco.milepost, dist)
            if not new_mp:
                err_str = ' - At end of track. Reversing.'
                track_log.info(loco.name + err_str)
                loco.direction *= -1
            else:
                _set_heading(loco.milepost, new_mp)
                loco.milepost = new_mp
                makeup_dist = dist

                # Determine base stations in range of current position
                loco.bases_inrange = [b for b in loco.track.bases.values()
                                      if b.covers_milepost(loco.milepost)]


def loco_messaging(loco):
    """ Real-time simulation of a locomotives's messaging system. Maintains
        connections to bases in range of loco position and sends/fetches msgs.
    """
    while loco.sim.running:
        sleep(MSG_INTERVAL)  # Sleep for specified interval

        # Drop all out of range base connections and keep alive existing
        # in-range connections
        lconns = loco.conns.values()
        for conn in [c for c in lconns if c.connected() is True]:
            if conn.connected_to not in loco.bases_inrange:
                conn.disconnect()
            else:
                conn.keep_alive()

        open_conns = [c for c in lconns if c.connected() is False]
        used_bases = [c.connected_to for c in lconns if c.connected() is True]
        for i, conn in enumerate(open_conns):
            try:
                if loco.bases_inrange[i] not in used_bases:
                    conn.connect(loco.bases_inrange[i])
            except IndexError:
                break  # No (or no more) bases in range to consider
            
        # Ensure at least one active connection
        conns = [c for c in lconns if c.connected() is True]
        if not conns:
            err_str = ' skipping msg send/recv - No active comms.'
            track_log.warn(loco.name + err_str)
            continue  # Try again next iteration

        # Send status msg over active connections, breaking on first success.
        status_msg = get_6000_msg(loco)
        for conn in conns:
            try:
                conn.send(status_msg)
                info_str = ' -  Sent status msg over ' + conn.connected_to.ID
                track_log.info(loco.name + info_str)
            except Exception as e:
                track_log.warn(loco.name + ' send failed: ' + str(e))
                
        # Fetch incoming cad msgs over active connections, breaking on success.
        for conn in conns:
            cad_msg = None
            try:
                cad_msg = conn.fetch(loco.emp_addr)
            except Queue.Empty:
                break  # No msgs (or no more msgs) to receive.
            except Exception as e:
                track_log.warn(loco.name + ' fetch failed: ' + str(e))
                continue  # Try the next connecion

            # Process cad msg, if msg and if actually for this loco
            if cad_msg and cad_msg.payload.get('ID') == loco.ID:
                try:
                    # TODO: Update track restrictions based on msg
                    track_log.info(loco.name + ' - CAD msg processed.')
                except:
                    track_log.error(loco.name + ' - Received invalid CAD msg.')
                break  # Either way, the msg was fetched # TODO: ACK w/broker?
        else:
            err_str = ' - active connections exist, but msg fetch/recv failed.'
            track_log.error(loco.name + err_str)


def base_messaging(self):
    """ Real-time simulation of a base station's messaging system
    """
    raise NotImplementedError


def wayside_messaging(self):
    """ Real-time simulation of a wayside's messaging system
    """
    raise NotImplementedError
