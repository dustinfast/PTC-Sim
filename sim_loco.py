""" loco.py - Simulates a locomotive traveling on a railroad track and
    sending/receiving status/command messages. See README.md for more info.

Author: Dustin Fast, 2018
"""

from time import time, sleep
from random import randint
from threading import Thread
from optparse import OptionParser
from ConfigParser import RawConfigParser
from math import degrees, radians, sin, cos, atan2
from Queue import Empty

from lib import Track, Loco, REPL
from msg_lib import Client, Message

# Init conf
config = RawConfigParser()
config.read('conf.dat')

# Import conf data
REFRESH_TIME = float(config.get('misc', 'refresh_sleep_time'))
LOCO_START_DIR = config.get('loco', 'start_direction')
LOCO_START_MP = float(config.get('loco', 'start_milepost'))
LOCO_START_SPEED = float(config.get('loco', 'start_speed'))
BROKER = config.get('messaging', 'broker')
MSG_INTERVAL = int(config.get('messaging', 'msg_interval'))
SEND_PORT = int(config.get('messaging', 'send_port'))
FETCH_PORT = int(config.get('messaging', 'fetch_port'))
BOS_EMP = config.get('messaging', 'bos_emp_addr')
LOCO_EMP_PREFIX = config.get('messaging', 'loco_emp_prefix')

# Symbolic constants
INCREASING = 'increasing'
DECREASING = 'decreasing'

class LocoSim(Loco):
    """ A simulated locomotive, including its messaging system.Travels up/down
        a track and sends/fetches messages.
    """
    def __init__(self, 
                 id_number=str(randint(1000, 9999)),
                 broker=BROKER,
                 broker_send_port=SEND_PORT,
                 broker_fetch_port=FETCH_PORT,
                 emp_prefix=LOCO_EMP_PREFIX,
                 broker_emp=BOS_EMP,
                 start_mp=LOCO_START_MP,
                 start_dir=LOCO_START_DIR,
                 start_speed=LOCO_START_SPEED):
        """ Instantiates a locomotive simulation.
        """
        # Locomotive
        Loco.__init__(self, id_number)
        self.track = Track()
        self.mph = start_speed
        self.direction = start_dir

        # Current milepost
        self.milepost = self.track.get_milepost_at(start_mp)
        if not self.milepost:
            raise ValueError('No milepost exists at the given start_mp')

        # Simulation
        self.running = False
        self.makeup_dist = 0
        self.loco_emp = emp_prefix + id_number 
        self.broker_emp = broker_emp
        self.msg_client = Client(broker, broker_send_port, broker_fetch_port)
        self.movement_thread = Thread(target=self._movement)
        self.messaging_thread = Thread(target=self._messaging)

    def status(self):
        """ Prints the simulation/locomotive status to the console.
        """
        pnt_str = 'Loco ID: ' + self.ID + '\n'
        pnt_str += 'Sim: ' + {True: 'on', False: 'off'}.get(self.running) + '\n'
        pnt_str += 'Speed: ' + str(self.mph) + ' mph\n'
        pnt_str += 'DOT: ' + self.direction + '\n'
        pnt_str += 'MP: ' + str(self.milepost) + '\n'
        pnt_str += 'Lat: ' + str(self.milepost.lat) + '\n'
        pnt_str += 'Long: ' + str(self.milepost.long) + '\n'
        pnt_str += 'Heading: ' + self.heading + '\n'
        pnt_str += 'Current base: ' + self.current_base + '\n'
        pnt_str += 'Bases in range: ' + \
                   ', '.join(b.ID for b in self.bases_inrange) + '\n'

        print(pnt_str)

    def start(self):
        """ Starts the simulator threads. 
        """
        self.running = True
        self.movement_thread.start()
        self.messaging_thread.start()
        print('Loco ' + self.ID + ': Simulation started...')

    def stop(self):
        """ Stops the simulator threads.
        """
        if self.running:
            # Signal stop to threads and join
            self.running = False
            self.movement_thread.join(timeout=REFRESH_TIME)
            self.messaging_thread.join(timeout=REFRESH_TIME)

            # Redefine threads, to allow starting after stopping
            self.movement_thread = Thread(target=self._movement)
            self.messaging_thread = Thread(target=self._messaging)
            print('Loco ' + self.ID + ': Simulation Stopped.')

    def _messaging(self):
        """ The loco messaging simulator thread. Sends status msgs and 
            receives/processes inbound command msgs every MSG_INTERVAL seconds.
        """
        while self.running:
            # Build status msg
            msg_type = 6000
            msg_source = self.loco_emp
            msg_dest = self.broker_emp

            payload = {'sent': time(),
                       'loco': self.ID,
                       'speed': self.mph,
                       'heading': self.heading,
                       'lat': self.milepost.lat,
                       'long': self.milepost.long,
                       'base': self.current_base}

            status_msg = Message((msg_type,
                                  msg_source,
                                  msg_dest,
                                  payload))

            # Send status message
            try:
                self.msg_client.send_msg(status_msg)
                print('Loco: Msg Send success')
            except Exception as e:
                print('Loco: Msg send failed due to: ' + str(e))

            # Receive and process the next available cmd message, if any
            cmd_msg = None
            try:
                cmd_msg = self.msg_client.fetch_next_msg(self.loco_emp)
            except Empty:
                print('Loco: No msg avaiable to fetch.')
            except Exception as e:
                print('Loco: Msg fetch failed due to: ' + str(e))
            
            # Process msg, ensuring that its actually for this loco
            if cmd_msg and cmd_msg.payload.get('loco') == self.ID:
                try:
                    content = cmd_msg.payload
                    self.speed = content['speed']
                    self.direction = content['direction']
                    print('Loco: Cmd msg fetched and processed.')
                except:
                    print('Loco: Malformed cmd msg recevied.')

            sleep(MSG_INTERVAL)

    def _movement(self):
        """ The loco movement simulator thread. Refreshes every STATUS INTERVAL
            seconds.
        """
        while self.running:
            # Move loco, if at speed
            if self.mph > 0:
                # Determine dist traveled since last iteration, including
                # makeup distance, if any.
                hours = REFRESH_TIME / 3600.0  # Seconds to hours, for mph
                dist = self.mph * hours * 1.0  # distance = speed * time
                dist += self.makeup_dist 

                # Set sign of dist based on dir of travel
                if self.direction == DECREASING:
                    dist *= -1

                # Get next milepost and any makeup distance
                new_mp, dist = self.track._get_next_mp(self.milepost, dist)
                if not new_mp:
                    print('End of track reached... Changing direction of travel.')
                    self.direction *= -1
                else:
                    self._set_heading(self.milepost, new_mp)
                    self.milepost = new_mp
                    self.makeup_dist = dist

                    # Determine base stations in range of current position
                    self.base_conns = []
                    for base in self.track.bases.values():
                        if base.covers_milepost(self.milepost):
                            self.base_conns.append(base)
                    print('Bases in range:' + str([b.ID for b in self.base_conns]))

            sleep(MSG_INTERVAL)

    def _set_heading(self, prev_mp, curr_mp):
        """ Sets loco heading based on current and prev milepost lat/long
        """
        lat1 = radians(prev_mp.lat)
        lat2 = radians(curr_mp.lat)

        long_diff = radians(prev_mp.long - curr_mp.long)

        x = sin(long_diff) * cos(lat2)
        y = cos(lat1) * sin(lat2) - (sin(lat1) * cos(lat2) * cos(long_diff))   
        deg = degrees(atan2(x, y))
        compass_bearing = (deg + 360) % 360

        self.heading = compass_bearing


if __name__ == '__main__':
    # Check cmd line args
    opts = OptionParser()
    opts.add_option('-b', action='store_true', dest='bos',
                    help='Accept commands via msging system (vs. command line)')
    (options, args) = opts.parse_args()

    # Init the loco simulator
    loco = LocoSim()

    # If BOS mode, loco receives commands from the BOS,
    # else, loco receives commands from the cmd line.
    if options.bos:
        pass  # TODO: BOS mode.
    else:
        # Init the Read-Eval-Print-Loop and start it
        welcome = ('-- Loco Sim Locotive Simulator --\nTry "help" for assistance.')
        repl = REPL(loco, 'Loco >> ', welcome)
        exit_cond = 'running == False'
        repl.add_cmd('start', 'start()')  # TODO: Allow cmd params
        repl.add_cmd('stop', 'stop()')
        repl.set_exitcmd('stop')
        repl.start()
