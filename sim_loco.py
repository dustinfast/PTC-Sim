#!/usr/bin/env python
""" loco.py - Simulates a locomotive traveling on a railroad track and
    sending/receiving status/command messages. See README.md for more info.

    Author: Dustin Fast, 2018
"""

from time import sleep
from random import randint
from threading import Thread
from ConfigParser import RawConfigParser
from math import degrees, radians, sin, cos, atan2

from sim_lib import Track, Loco, Client, Queue, Message, REPL, logger

# Init conf
config = RawConfigParser()
config.read('conf.dat')

# Import conf data
REFRESH_TIME = float(config.get('application', 'refresh_time'))
START_DIR = config.get('locomotive', 'start_direction')
START_MP = float(config.get('locomotive', 'start_milepost'))
START_SPEED = float(config.get('locomotive', 'start_speed'))
MSG_INTERVAL = int(config.get('messaging', 'msg_interval'))
BOS_EMP = config.get('messaging', 'bos_emp_addr')
EMP_PREFIX = config.get('messaging', 'loco_emp_prefix')


class SimLoco(Loco):
    """ A simulated locomotive, including its messaging system. Travels up/down
        a track and sends status msgs/fetches cmd messages on self.start().
    """
    def __init__(self, locoID=randint(1000, 9999)):
        """ Instantiates a locomotive simulation.
        """
        # Locomotive
        Loco.__init__(self, str(locoID))
        self.track = Track()
        self.speed = START_SPEED
        self.direction = START_DIR
        self.disp_str = 'Loco ' + self.ID + ' -'  # For log output convenience

        # Current milepost
        self.milepost = self.track.get_milepost_at(START_MP)
        if not self.milepost:
            raise ValueError('No milepost exists at the given start milepost')

        # Simulation 
        self.running = False
        self.repl_started = False
        self.makeup_dist = 0
        self.movement_thread = Thread(target=self._movement)
        self.messaging_thread = Thread(target=self._messaging)

        # Messaging
        self.loco_emp = EMP_PREFIX + self.ID
        self.broker_emp = BOS_EMP
        self.msg_client = Client()

    def start(self, terminal=False):
        """ Starts the simulator threads. 
        """
        if not self.running:
            logger.info(self.disp_str + ' Simulation started.')
            
            self.running = True
            self.movement_thread.start()
            self.messaging_thread.start()

            if terminal and not self.repl_started:
                self.repl_started = True
                self._repl()

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
            logger.info(self.disp_str + ' Simulation stopped.')

    def status(self):
        """ Prints the locomotive and simulator status to the console.
        """
        status = self.get_status_dict()
        status['Sim'] = {True: 'running', False: 'off'}.get(self.running)

        print('\n'.join(status))

    def _messaging(self):
        """ The loco messaging simulator thread. Sends status msgs and 
            receives/processes inbound command msgs every MSG_INTERVAL seconds.
        """
        while self.running:
            # Build status msg
            msg_type = 6000
            msg_source = self.loco_emp
            msg_dest = self.broker_emp
            payload = str(self.get_status_dict())

            status_msg = Message((msg_type,
                                  msg_source,
                                  msg_dest,
                                  payload))

            # Send status message
            try:
                self.msg_client.send_msg(status_msg)
                logger.debug(self.disp_str + ' Sent status msg.')
            except Exception as e:
                logger.debug(self.disp_str + ' Status send failed: ' + str(e))

            # Receive and process the next available cmd message, if any
            cmd_msg = None
            try:
                cmd_msg = self.msg_client.fetch_next_msg(self.loco_emp)
            except Queue.Empty:
                logger.debug(self.disp_str + ' No msg available to fetch.')
            except Exception as e:
                logger.error(self.disp_str + ' Fetch failed - connection error.')
            
            # Process msg, ensuring that its actually for this loco
            if cmd_msg and cmd_msg.payload.get('loco') == self.ID:
                try:
                    content = cmd_msg.payload
                    self.speed = content['speed']
                    self.direction = content['direction']
                    logger.debug(self.disp_str + ' Cmd msg processed.')
                except:
                    logger.error(self.disp_str +  'Received malformed cmd msg.')

            sleep(MSG_INTERVAL)

    def _movement(self):
        """ The loco movement simulator thread. Refreshes every STATUS INTERVAL
            seconds.
        """
        while self.running:
            # Move loco, if at speed
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
                    info = ' End of track reached - Changing direction.'
                    logger.info(self.disp_str + info)
                    self.direction *= -1
                else:
                    self._set_heading(self.milepost, new_mp)
                    self.milepost = new_mp
                    self.makeup_dist = dist

                    # Determine base stations in range of current position
                    self.bases_inrange = [b for b in self.track.bases.values()
                                          if b.covers_milepost(self.milepost)]
                    self.baseID = None
                    if self.bases_inrange:
                        self.baseID = self.bases_inrange[0].ID
                    
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

    def _repl(self):
        """ Blocks while watching for terminal input, then processes it.
        """
        repl = REPL(self, '')
        repl.add_cmd('start', 'start()')
        repl.add_cmd('status', 'status()')
        repl.add_cmd('stop', 'stop()')
        repl.set_exitcmd('stop')
        repl.start()


if __name__ == '__main__':
    # Start the locomotive simulation in terminal mode
    print('-- LocoBOSS: Locomotive Simulator --')
    SimLoco().start(terminal=True)
