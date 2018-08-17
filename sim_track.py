#!/usr/bin/env python
""" loco.py - Simulates a locomotive traveling on a railroad track and
    sending/receiving status/command messages. See README.md for more info.

    Author: Dustin Fast, 2018
"""

from lib_app import REPL
from lib_track import Track


if __name__ == '__main__':
    ##############################
    # Start the track simulation #
    ##############################

    ptctrack = Track()
    try:

        # Start each device's sim
        for l in ptctrack.locos.values():
            l.sim.start()

        print("-- PTC Sim: Track Simulator - Type 'exit' to quit --\n")
        while True:
            for l in ptctrack.locos.values():
                print(str(l.speed) + ' @ ' + str(l.milepost.marker))
            
            uinput = raw_input('>>')
            if uinput == 'exit':
                print('Quitting...')
                break

    except Exception as e:
        print(e)

    # Stop each device's sim
    for l in ptctrack.locos.values():
        l.sim.stop()
    
