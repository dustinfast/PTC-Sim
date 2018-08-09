""" loco_sim.py -
Simulates a locomotive traveling on a railroad track. 

The user may interact with this module via command line or the Back Office
Server. 

See README.md for more info.

Author:
    Dustin Fast, 2018
"""

import json
import ConfigParser
from time import sleep
from threading import Thread
from optparse import OptionParser
from math import degrees, radians, sin, cos, atan2
from sim_lib import print_err
from sim_lib import Base, Milepost

# Init constants from config file
try:
    config = ConfigParser.RawConfigParser()
    config.read('conf.dat')

    TRACK_RAILS = config.get('loco', 'track_rails')
    TRACK_BASES = config.get('loco', 'track_bases')
    LOCO_START_DIR = config.get('loco', 'start_direction')
    LOCO_START_HEADING = config.get('loco', 'start_heading')
    LOCO_START_MP = config.get('loco', 'start_milepost')  
    LOCO_START_SPEED = float(config.get('loco', 'start_speed'))
    LOCO_SIM_REFRESH = int(config.get('loco', 'sim_refresh'))
except ConfigParser.NoSectionError:
    errstr = 'Error loading configuration file - Ensure conf.dat exists '
    errstr += 'and contains necessary section headers.'
    raise ConfigParser.NoSectionError(errstr)
except ConfigParser.NoOptionError:
    errstr = 'Error reading configuration file - One or more required options '
    errstr += 'are missing in conf.dat.'
    raise ConfigParser.NoSectionError(errstr)


##############
#  Classes   #
##############

class _Track(object):  # TODO: Move to lib?
    """ A representation of the track our virtual train travels, including 
        radio communication base stations and their associated coverage areas.
    
        self.bases = A dict of radio base stations, used by locos  to send msgs. 
            Format: { BASEID: BASE_OBJECT }
        self.mp_objects = Used to associate BRANCH/MP with MPOBJ.
            Format: { MP: MPOBJ }
        self.mp_linear = A representation of the track in order of mps.
            Format: [ MP1, ... , MPn ], where MP1 < MPn
        self.mp_linear = A represention the track in reverse order of mps.
            Format: [ MPn, ... , MP1], where MP1 < MPn
        Note: BASEID = string, MP/lat/long = floats, MPOBJs = Milepost objects.
    """
    def __init__(self):
        self.bases = {}
        self.mp_objects = {}
        self.mp_linear = []
        self.mp_linear_rev = []

        # Populate self.bases from TRACK_BASES json
        print('Populating Base Stations...')
        try:
            with open(TRACK_BASES) as base_data:
                bases = json.loads(base_data.read())
        except Exception as e:
            raise Exception('Error reading ' + TRACK_BASES + ': ' + str(e))

        for b in bases:
            try:
                baseID = b['id']
                coverage_start = float(b['coverage'][0])
                coverage_end = float(b['coverage'][1])
            except ValueError:
                print('WARNING: Discarding base "' +
                      baseID + '": Conversion Error')
                continue
            except KeyError:
                raise Exception(
                    'Improperly formatted JSON encountered in get_mileposts()')

            self.bases[baseID] = Base(baseID, coverage_start, coverage_end)

        # Populate self.mp_objects from TRACK_RAILS json
        print('Populating Mileposts...')
        try:
            with open(TRACK_RAILS) as rail_data:
                mileposts = json.loads(rail_data.read())
        except Exception as e:
            raise Exception('Error reading ' + TRACK_RAILS + ': ' + str(e))

        # Build self.mp_objects dict
        for m in mileposts:
            try:
                mp = float(m['milemarker'])
                lat = float(m['lat'])
                lng = float(m['long'])
            except ValueError:
                print('WARNING: Discarding mp "' + str(mp) + '": Conversion Error')
                continue
            except KeyError:
                raise Exception(
                    'Improperly formatted JSON encountered in get_mileposts()')

            self.mp_objects[mp] = Milepost(mp, lat, lng)

        # Populate self.mp_linear and self.mp_linear_rev from self.mp_objects
        for mp in sorted(self.mp_objects.keys()):
            self.mp_linear.append(mp)
        self.mp_linear_rev = self.mp_linear[::-1]

    def _get_next_mp(self, curr_mp, distance):
        """ Given a curr_mp and distance, returns the nearest mp marker for
            curr_mp + distance and also returns the difference between curr_mp 
            + distance and that next mp marker.
            Accepts:
                curr_mp  = Curr location (a Milepost)
                distance = Distance in miles (neg dist denotes decreasing DOT)
            Returns:
                next_mp   = nearest mp for curr_mp + distance without going over
                dist_diff = difference between next_mp and actual location
            Note: If next_mp = curr_mp, diff = distance.
        """
        # If no distance, next_mp = curr_mp
        if distance == 0:
            return curr_mp, distance

        # Working vars
        mp = curr_mp.mp
        target_mp = mp + distance
        dist_diff = 0
        next_mp = None

        # Set mp list to iterate, depending on direction
        if distance > 0:
            mps = self.mp_linear
        elif distance < 0:
            mps = self.mp_linear_rev

        # Find next mp marker, noting diff between next mp and actual location
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
            
        # If we didn't find a marker, next_mp = curr_mp because end of track.
        if not next_mp:
            print('Warning: Next mp is beyond end of track ')
            next_mp = mp

        # Get mp object associated with next_mp
        next_mp_obj = self._get_mp_obj(next_mp)
        if not next_mp_obj:
            # Print debug info
            print(str(mps))
            print('cur_mp: ' + str(mp))
            print('moved : ' + str(distance))
            print('tgt_mp: ' + str(target_mp))
            print('mp_idx: ' + str(i))
            print('nxt_mp: ' + str(next_mp))
            print('disdif: ' + str(dist_diff))
            raise Exception('Could not find next mp for loco.')
        
        return next_mp_obj, dist_diff

    def _get_mp_obj(self, mp):
        """ Returns the MP object for the given mp (a float), if exists. Else,
            returns None.
        """
        return self.mp_objects.get(mp, None)


class _LocoSim(object):
    """ A simulated locomotive on the track.
        Contains it's own thread that updates loco properties as it moves. 
        Assumes only one instance of itself ever exists at a time.
    """
    def __init__(self):
        # Locomotive properties
        self.mph = LOCO_START_SPEED
        self.dot = LOCO_START_DIR
        self.heading = LOCO_START_HEADING
        self.ID = '7357'  # TODO: Randomize ID
        self.radio_up = True
        self.base_conns = []

        # Locomotive milepost
        self.milepost = g_track._get_mp_obj(LOCO_START_MP)
        if not self.milepost:
            errstr = 'ERROR: No mp found for start mp ' + LOCO_START_MP + ' - '
            errstr += 'Simulation behavior may be unpredictable.'
            print_err(errstr)
        
        # Simulation thread vars
        self.sim_on = False
        self.sim_thread = Thread(target=self._simulate)
        self.dist_makeup = 0  # Diff between the current mp and actual location

    def __str__(self):
        ret_str = 'Loco ' + self.ID + ' at mp '
        ret_str += str(self.milepost) + ' going ' + str(self.mph) + 'mph'
        return ret_str
        
    def _simulate(self):
        """ Loco movement simulator. Call this func only as a thread. 
            Iterates every LOCO_SIM_REFRESH seconds.
        """
        while self.sim_on:
            # Move loco, if at speed
            if self.mph > 0:
                # Determine dist traveled since last iter
                thours = LOCO_SIM_REFRESH / 3600.0  # Seconds to hours
                dist = self.mph * thours * 1.0  # dist = speed * time
                dist += self.dist_makeup  # Add any dist to make up

                # Set sign of dist, depending on dir of travel
                if self.dot == 'decreasing':
                    dist = dist * -1

                # get next mp and any distance to make up in the next iteration.
                new_mp, dist = g_track._get_next_mp(self.milepost, dist)
                if new_mp:
                    self._set_heading([self.milepost.lat, self.milepost.long],
                                      [new_mp.lat, new_mp.long])
                    self.milepost = new_mp
                    self.dist_makeup = dist
                else:
                    raise Exception('No new MP returned from get_next_mp()')
                    
            # Update 220 radio (base station) connections
            self._update_base_conns()

            # Send status msg
            # send_status(self.ID,
            #             str(self.milepost.lat),
            #             str(self.milepost.long),
            #             str(self.mph), self.heading)

            sleep(LOCO_SIM_REFRESH)

    def _update_base_conns(self):
        """ Sets self.base_conns according to the bases covering self.milepost
        """
        # If loco's radio down, no base conns
        if not self.radio_up:
            self.base_conns = []
            return 

        # Determine 220 radio base station connections
        self.base_conns = []        
        for base in g_track.bases.values():
            if base.covers_mp(self.milepost.mp):
                self.base_conns.append(base)

        # print('Bases in range:' + str([b.ID for b in self.base_conns]))  # debug
        
    def _set_heading(self, pointA, pointB):
        """
        Takes two points, each a list [lat, long] calculates the
        heading to travel between them and sets it to self.heading.
        """
        lat1 = radians(pointA[0])
        lat2 = radians(pointB[0])

        diffLong = radians(pointB[1] - pointA[1])

        x = sin(diffLong) * cos(lat2)
        y = cos(lat1) * sin(lat2) - (sin(lat1) * cos(lat2) * cos(diffLong))
        initial_bearing = atan2(x, y)
        initial_bearing = degrees(initial_bearing)
        compass_bearing = (initial_bearing + 360) % 360

        self.heading = str(compass_bearing)[:str(compass_bearing).find(".") + 2]
 
    def _get_status(self, ret_dict=False):
        """ Returns the loco status in either string or dict form. (Dict form is
            for webmode.)
        """
        # build status dict
        status = {}
        status['Loco ID   : '] = self.ID
        status['Sim       : '] = {True: 'on', False: 'off'}.get(self.sim_on)
        status['Speed     : '] = str(self.mph)
        status['DOT       : '] = self.dot
        status['MP        : '] = str(self.milepost)
        status['Lat       : '] = str(self.milepost.lat)
        status['Long      : '] = str(self.milepost.long)
        status['Heading   : '] = self.heading
        status['220 Radio : '] = {True: 'up', False: 'down'}.get(self.radio_up)
        status['Bases     : '] = ', '.join(b.ID for b in self.base_conns)

        if ret_dict:
            return status
        else:
            ret_str = ''
            for k, v in status.iteritems():
                ret_str += k + v + '\n'

            return ret_str

    def status(self):
        """ Echoes locomotive status.
            Usage: loco status
        """
        print(self._get_status())

    def sim(self, action=None):
        """ Starts or stops the locomotive simulation thread.
            Usage: loco sim ( start | stop )
        """
        if action == 'start':
            if self.sim_on:
                print('Simulation already running.')
                return
            self.sim_on = True
            self.sim_thread = Thread(target=self._simulate)     
            self.sim_thread.start()
            print('Simulation started.')
            self.status
        elif action == 'stop':
            if self.sim_on:
                self.sim_on = False
                self.sim_thread.join()
                self.base_conns = []  # Reset base station connections
                print('Sim stopped.')
            else:
                print('Sim already stopped.')
        else:
            print_err("Invalid action '" + action + "'", "( start | stop )")
            # TODO: Validate options

    def speed(self, mph=None):
        """ Sets the locomotive's current speed. 
            Usage: loco speed [ new_speed ]
        """
        try:
            mph = float(mph)
            if mph >= 100.0:
                print_err('Speed must be less than 100 mph')
            else:
                self.mph = mph
        except: 
            print_err('Speed must be numeric')

    def direction(self, dot=None):
        """ Sets the locomotive's current direction of travel. 
            Usage: loco direction ( increasing | decreasing )
        """
        # TODO: Use validate options
        if dot != 'increasing' and dot != 'decreasing':
            print_err("Invalid DOT '" + dot + "'", "( increasing | decreasing )")
            return

        self.dot = dot

    def mp(self, mp_string=None):
        """ Sets the locomotive's current milepost. 
            Usage: loco mp [ new_milepost ]
        """
        if not mp_string:
            print_err('No milepost given')
        else:
            try:
                mp = float(mp_string)
                self.milepost = g_track.mp_objects[mp]
            except ValueError:
                print_err('Milepost must be numeric')
            except:
                err = mp_string + ' does not correspond to a mapped milepost'
                print_err(err)


########
# REPL #
########

def start(boss_mode=None):
    """ Starts the tool, including the REPL.
        If not in webmode, input/output is via terminal. Else, all input is 
        received via HTTP and all output (including print statements) is 
        redirected to HTTP.
        Once this function is called, the only graceful exit is an input of 'q'.
    """
    print('Initializing...')
    
    # Instantiate objects
    global g_track
    g_track = _Track()
    loco = _LocoSim()

    # Ini prompt, show welcome, and build help
    print('\n--- Loco Sim ---')
    print("Type q to exit. \n")
    
    # REPL
    while True:
        # Block until a cmd is received. If boss_mode, cmds are recv'd from the
        # BOS via messages over TCP/IP, else they're received via command line.
        if boss_mode:
            pass
            #TODO: Check for new msgs - QPID?
            # 
            # if timeout:
            #   continue 
        else:
            uinput = raw_input('LT >> ').strip()

        # On blank input, continue.
        if not uinput:
            continue
        # On exit, break.
        elif uinput == 'q':
            break
        # On malformed input (i.e. no whitespace seperator), continue
        elif ' ' not in uinput:
            print_err('Malformed command')
            continue
        
        # TODO: all cmds starts with 'loco'
        # Explode user input on whitespace to build device, cmd, and args
        uinput = uinput.split(' ')
        device = uinput[0]
        cmd = uinput[1]
        args = uinput[2:]

        # Build eval string from cmd
        arg_string = str(args).replace('[', '').replace(']', '')
        eval_string = device.lower() + '.' + cmd + '(' + arg_string + ')'

        # Attempt to evaluate command
        # print('--DEBUG INFO: Evaluating "' + eval_string + '"...')
        # try:
        #     if boss_mode:
        #         print(' '.join(uinput))
        eval(eval_string)
        # except Exception as e:
        #     print_err('Malformed command', CMDFORMAT)
        #     # print('--DEBUG INFO: ' + str(e))  # debug

    # On exit, do cleanup
    if loco.sim_on:  
        print('Stopping threads...')
        loco.sim('stop')


if __name__ == '__main__':
    # Check cmd line args
    opts = OptionParser()
    opts.add_option('-b', action='store_true', dest='bos',
                    help='Accept commands via msging system (vs. command line)')
    (options, args) = opts.parse_args()

    # Start the interface
    start(options.bos)
    
