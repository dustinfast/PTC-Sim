#!/usr/bin/env python
""" Starts the Track Simulator, Message Broker, and Back Office Server,
    each as seperate processes, with Python's Multiprocessing lib.

    Author: Dustin Fast, 2018
"""

from time import sleep
import multiprocessing


class _process(multiprocessing.Process):
    """ Wraps the given module in a multiprocessing.Process.
        Assumes the given module contains a start() member.
    """
    def __init__(self, module_name, class_name):
        """ Accepts:
                module_name: A string denoting the module name
        """
        multiprocessing.Process.__init__(self)
        self.module_name = module_name
        self.class_name = class_name

    def run(self):
        """ Use reflection to import the module and start the given class.
        """
        expr = 'from ' + self.module_name
        expr += ' import ' + self.class_name + ' as mod'
        print(expr)
        exec(expr)

        mod().start()



if __name__ == '__main__':
    """ Start the PTC Sim application, with each component existing in a
        seperate process.
    """
    # Init a process for each top-level module and start them.
    sim_procs = []
    sim_procs.append(_process('sim_bos', 'BOS'))
    sim_procs.append(_process('sim_broker', 'Broker'))
    sim_procs.append(_process('sim_track', 'TrackSim'))

    [p.start() for p in sim_procs]

    sleep(.5)  # Prevent console output overlap by allowing procs time to start.

    print('-- PTC Sim: A Positive Train Control Demonstration')
    print('-- Navigate to https://localhost:5000/ptc_sim for web interface.')
    print("-- Type 'exit' to quit.")

    while True:
        try:
            uinput = raw_input('>> ')
        except KeyboardInterrupt:
            uinput = None

        if uinput == 'exit':
            print('Stopping processes...')
            [p.terminate() for p in sim_procs]

            try:
                [p.join(timeout=5) for p in sim_procs]

            except:
                e = 'Timed out wating for one or more subprocesses to close.'
                raise Exception(e)
            break
        else:
            continue

