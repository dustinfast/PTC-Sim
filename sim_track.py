#!/usr/bin/env python
""" loco.py - Simulates a locomotive traveling on a railroad track and
    sending/receiving status/command messages. See README.md for more info.

    Author: Dustin Fast, 2018
"""

from time import sleep
from threading import Thread

from lib_app import REPL, REFRESH_TIME
from lib_track import Track, track_logger


class TrackSim(object):
    """ The Track Simulator. Consists of three seperate threads:
        Msg Receiver  - Watchers for incoming messages over TCP/IP.
        Fetch Watcher - Watches for incoming fetch requests over TCP/IP and
                        serves msgs as appropriate.
    """
    def __init__(self):
        self.running = False  # Thread kill flag
        self.tracksim_thread = Thread(target=self._tracksim)  # Tracksim thread

    def start(self):
        """ Start the message broker threads
        """
        if not self.running:
            track_logger.info('Track Sim Starting...')
            self.running = True
            self.tracksim_thread.start()

    def stop(self):
        """ Stops the msg broker. I.e., the msg receiver and fetch watcher 
            threads. 
        """
        if self.running:
            # Signal stop to threads and join
            self.running = False
            self.tracksim_thread.join(timeout=REFRESH_TIME)

            # Redefine thread, to allow starting after stopping
            self.tracksim_thread = Thread(target=self._tracksim)

            track_logger.info('Track Sim stopped.')

    def _tracksim(self):
        """ The Track simulator - Currently only simulates locomotives
            traveling on a track.
        """
        ptctrack = Track()
        
        while self.running:
            try:
                # Start each track componenet-device's simulation thread
                # These devices exists "on" the track and simulate their own 
                # operation.
                for l in ptctrack.locos.values():
                    l.sim.start()

                for l in ptctrack.locos.values():
                        print(str(l.speed) + ' @ ' + str(l.milepost.marker))

            except Exception as e:
                print(e)

            sleep(REFRESH_TIME)

        # Stop each device's sim thread.
        print('Stopping sims...')
        for l in ptctrack.locos.values():
            l.sim.stop()


if __name__ == '__main__':
    # Start the track simulation in REPL/Terminal mode
    print("-- PTC Sim: Track Simulator - Type 'exit' to quit --\n")
    sim = TrackSim()
    sim.start()    
    REPL(sim).get_repl().start()
    


    
