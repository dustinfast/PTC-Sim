#!/usr/bin/env python
""" Starts the necessary services and processes for LocoBOSS with 3 random
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
    # TODO: No log output to console - web disp only
    # TODO: Instantiate demo locos with random start/direction/speed
    """ Start the LocoBOSS application and web service, with each component
        existing in a seperate process.
    """

    print('-- Locomotive Back Office Server Simulation --')
    print('Navigate to https://localhost:5000/LocoBOSS for web interface.')
    print("Use 'exit' to shutdown.")


    # Start the componenets
    loco_proc = _process('sim_loco', 'SimLoco')
    broker_proc = _process('sim_broker', 'Broker')
    bos_proc = _process('sim_bos', 'BOS')
    loco_proc.start()
    broker_proc.start()
    bos_proc.start()

    while True:
        uinput = raw_input('>> ')
        
        if uinput == 'exit':
            loco_proc.terminate()
            broker_proc.terminate()
            bos_proc.terminate()
            break
        else:
            continue

