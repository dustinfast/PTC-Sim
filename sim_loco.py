""" loco_sim.py -
Simulates a locomotive traveling on a railroad track. 

The user may interact with this module via command line or the Back Office
Server. 

See README.md for more info.

Author:
    Dustin Fast, 2018
"""

from time import time, sleep
from random import randint
from threading import Thread
from optparse import OptionParser
from ConfigParser import RawConfigParser
from math import degrees, radians, sin, cos, atan2

from lib import Track, Loco, REPL
from msg_lib import Client, Message

# Init conf
config = RawConfigParser()
config.read('conf.dat')

# Import conf data
REFRESH_TIME = float(config.get('misc', 'refresh_sleep_time'))
LOCO_START_DIR = config.get('loco', 'start_direction')
LOCO_START_HEADING = config.get('loco', 'start_heading')
LOCO_START_MP = config.get('loco', 'start_milepost')  
LOCO_START_SPEED = float(config.get('loco', 'start_speed'))
BROKER = config.get('messaging', 'broker')
SEND_PORT = int(config.get('messaging', 'send_port'))
FETCH_PORT = int(config.get('messaging', 'fetch_port'))
BOS_EMP = config.get('messaging', 'bos_emp_addr')
LOCO_EMP_PREFIX = config.get('messaging', 'loco_emp_prefix')

# Symbolic constants
INCREASING = 'increasing'
DECREASING = 'decreasing'

class LocoSim(Loco):
    """ A simulated locomotive, including its messaging system.
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
        """
        """
        # Locomotive
        Loco.__init__(self, id_number)
        self.track = Track()
        self.curr_milepost = self.track._get_mp_obj(start_mp)
        self.mph = start_speed
        self.direction = start_dir

        # Simulation
        self.running = False
        self.dist_makeup = 0
        self.loco_emp = emp_prefix + id_number 
        self.broker_emp = broker_emp
        self.msg_client = Client(broker, broker_send_port, broker_fetch_port)
        self.travel_thread = Thread(target=self._movement)
        self.messaging_thread = Thread(target=self._messaging)

    def status(self):
        """ Prints the simulation/locomotive status to the console.
        """
        ret_str = 'Loco ID: ' + self.ID + '\n'
        ret_str += 'Sim: ' + {True: 'on', False: 'off'}.get(self.running) + '\n'
        ret_str += 'Speed: ' + str(self.mph) + ' mph\n'
        ret_str += 'DOT: ' + self.direction + '\n'
        ret_str += 'MP: ' + str(self.milepost) + '\n'
        ret_str += 'Lat: ' + str(self.milepost.lat) + '\n'
        ret_str += 'Long: ' + str(self.milepost.long) + '\n'
        ret_str += 'Heading: ' + self.heading + '\n'
        ret_str += 'Current base: ' + self.current_base + '\n'
        ret_str += 'Bases in range: ' + \
                   ', '.join(b.ID for b in self.bases_inrange) + '\n'

        print(ret_str)

    def start(self):
        """ Starts the message sending/receving thread. 
        """
        self.running = True
        self.travel_thread.start()
        self.messaging_thread.start()
        print('Loco ' + self.ID + ': Messaging started...')

    def stop(self):
        """ Stops the message sending/receving thread.
        """
        if self.running:
            self.running = False
            self.travel_thread.join(timeout=REFRESH_TIME)
            self.messaging_thread.join(timeout=REFRESH_TIME)
            self.messaging_thread = Thread(target=self._movement)
            self.messaging_thread = Thread(target=self._messaging)
        print('Loco ' + self.ID + ': Messaging Stopped.')

    def _messaging(self):
        """ The loco messaging simulator thread. Sends status msgs and 
            receives/processes inbound command msgs every REFRESH_TIME seconds.
        """
        # Init messageing client

        while self.running:
            # Build status msg
            msg_type = 6000
            msg_source = self.loco_emp
            msg_dest = self.broker_emp

            payload = {'sent': time.now(),
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
            self.msg_client.send_msg(status_msg)

            # Receive and process any available cmd messages            
            try:
                cmd_msg = self.msg_client.fetch_next_msg(self.loco_emp)
            except:
                # Either msg transfer failed or there was no message to fetch.
                cmd_msg = None  # implicit, shown here for clarity
            
            # Process msgs, ensuring they're for this loco
            if cmd_msg and cmd_msg.get('loco') == self.ID:
                try:
                    content = cmd_msg.payload
                    self.curr_milepost = self.track._get_mp_obj(content['mp'])
                    self.speed = content['speed']
                    self.direction = content['direction']
                except:
                    print('Malformed cmd msg recevied.')

            sleep(REFRESH_TIME)

    def _movement(self):
        """ The loco movement simulator thread. Refreshes every REFRESH_TIME 
            seconds.
        """
        while self.running:
            # Move loco, if at speed
            if self.mph > 0:
                # Determine dist traveled since last iter
                thours = REFRESH_TIME / 3600.0  # Seconds to hours
                dist = self.mph * thours * 1.0  # dist = speed * time
                dist += self.dist_makeup  # Add any dist to make up

                # Set sign of dist, depending on dir of travel
                if self.dot == DECREASING:
                    dist = dist * -1

                # get next mp and any distance to make up in the next iteration.
                new_mp, dist = self.track._get_next_mp(self.milepost, dist)
                if new_mp:
                    self._set_heading([self.milepost.lat, self.milepost.long],
                                      [new_mp.lat, new_mp.long])
                    self.milepost = new_mp
                    self.dist_makeup = dist
                else:
                    raise Exception('No new MP returned from get_next_mp()')

            # Update radio base station connections
            self._update_base_conns()

            sleep(REFRESH_TIME)


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
        repl = REPL(loco, prompt='Loco>> ')
        exit_cond = 'running == False'
        repl.set_exitcond(exit_cond, 'Cannot exit while running. Try "stop" first')
        repl.add_cmd('start', 'start()')  # TODO: Allow cmd params
        repl.add_cmd('stop', 'stop()')
        repl.start()
