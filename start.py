#!/usr/bin/env python
""" Starts the Track Simulator, Message Broker, and Back Office Server,
    each as seperate processes in their own memory space with Python's 
    Multiprocessing lib.

    Author: Dustin Fast, 2018
"""

from time import sleep
import multiprocessing

from lib_app import APP_NAME, dep_install

# Attempt to import dependencies and prompt in fail. Note that these modules
# are not used in this file, but some processes it starts depend on them.
try:
    from flask import Flask, render_template, jsonify, request
except:
    dep_install('Flask')
try:
    from flask_googlemaps import GoogleMaps
except:
    dep_install('flask_googlemaps')

class _process(multiprocessing.Process):
    """ Wraps the given module in a multiprocessing.Process and provides a 
        run() interface. Assumes the given module contains a start() member.
    """
    def __init__(self, module_name, class_name, *args):
        """ Accepts module_name, a string denoting the module name
        """
        multiprocessing.Process.__init__(self)
        self.module_name = module_name
        self.class_name = class_name

    def run(self):
        """ Use reflection to import the given module and call its start()
        """
        expr = 'from ' + self.module_name
        expr += ' import ' + self.class_name + ' as mod'
        exec(expr)
        mod().start()  # Linter error ignorable here; linter it can't see def.


if __name__ == '__main__':
    """ Start the PTC-Sim application, with each component existing in a
        seperate process.
    """
    welcome = '** ' + APP_NAME + ': A Positive Train Control Demonstration.\n'
    welcome += '** Web interface at: https://localhost:5000/' + APP_NAME + '\n'
    welcome += "** Type 'exit' to quit.\n\n"
    print(welcome)

    sleep(1.5)  # Allow time to read welcome before screen is flooded

    # Init a process for each top-level module and start them.
    sim_procs = []
    sim_procs.append(_process('sim_bos', 'BOS'))
    sim_procs.append(_process('sim_broker', 'Broker'))
    sim_procs.append(_process('sim_track', 'TrackSim'))

    [p.start() for p in sim_procs]

    # Allow graceful quit with 'exit'.
    while True:
        try:
            uinput = raw_input('')
        except KeyboardInterrupt:
            uinput = None

        if uinput == 'exit':
            print('Stopping processes...')
            [p.terminate() for p in sim_procs]

            try:
                [p.join(timeout=5) for p in sim_procs]

            except:
                raise Exception('Timed out wating for subprocesses to close.')
            break
        else:
            print("Invalid input. Type 'exit' to quit.")
