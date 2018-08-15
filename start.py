#!/usr/bin/env python
""" Starts the necessary services and processes for PTC Sim with 3 random
    locomotives. The locomotives, message broker, and back office server are
    each started as seperate processes with Python's Multiprocessing lib.

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
        
        try:
            exec(expr)
            mod().start()
        except:
            raise ValueError('Invalid module: ', self.module_name)


if __name__ == '__main__':
    """ Start the PTC Sim application, with each component existing in a
        seperate process.
    """
    # Start the application componenets
    bos_proc = _process('sim_bos', 'BOS')
    broker_proc = _process('sim_broker', 'Broker')
    loco_proc = _process('sim_track', 'SimLoco')

    bos_proc.start()
    broker_proc.start()
    loco_proc.start()

    sleep(.5)  # Allow enough time for all to start

    print('-- PTC Sim: A Positive Train Control Demonstration')
    print('-- Navigate to https://localhost:5000/ptc_sim for web interface.')
    print("-- Type 'exit' to quit.")

    while True:
        uinput = raw_input('>> ')
        
        if uinput == 'exit':
            loco_proc.terminate()
            broker_proc.terminate()
            bos_proc.terminate()
            break
        else:
            continue

