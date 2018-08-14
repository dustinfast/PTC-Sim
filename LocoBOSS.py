#!/usr/bin/env python
""" Starts the necessary services and processes for LocoBOSS with 3 random
    locomotives. The locomotives, message broker, and back office server are
    each started as seperate processes with Python's Multiprocessing lib.

    Author: Dustin Fast, 2018
"""

import time
import multiprocessing


class _process(multiprocessing.Process):
    """ Starts the given component of LocoBOSS, either "loco", "broker", 
        or "bos" as a seperate process.
    """
    def __init__(self, module_name, signal_queue):
        multiprocessing.Process.__init__(self)
        self.module_name = module_name
        self.signal_queue = signal_queue
        self.obj = None

    def run(self):
        if self.module_name == 'loco':
            import sim_loco as module
            self.obj = module.SimLoco()
        elif self.module_name == 'broker':
            import sim_broker as module
            self.obj = module.Broker()
        elif self.module_name == 'bos':
            import sim_bos as module
            self.obj = module.BOS()
        else:
            raise ValueError(self.module_name)
        self.obj.start()

        # Stay alive until kill signal
        while True:
            time.sleep(1)
            try:
                self.signal_queue.get(timeout=1)
                self.obj.stop()
                break
            except:
                pass

if __name__ == '__main__':
    # TODO: No log output to console - web disp only
    # TODO: Instantiate demo locos with random start/direction/speed
    """ Start the LocoBOSS application and web service, with each component
        existing in a seperate process.
    """
    print('-- LocoBOSS --')
    print('Navigate to https://localhost:5000/LocoBOSS for web interface.')
    print("To shutdown, type 'exit' here or quit from web.")

    # Multiprocssing queues, for signaling kill to each process
    loco_signal = multiprocessing.Queue()
    broker_signal = multiprocessing.Queue()
    bos_signal = multiprocessing.Queue()

    # Start each component, sleeping to avoid initial overlapping output
    _process('loco', loco_signal).start()
    time.sleep(.5)
    _process('broker', broker_signal).start()
    time.sleep(.5)
    _process('bos', bos_signal).start()
    time.sleep(.5)

    # Init the REPL
    while True:
        uinput = raw_input('>> ')

        if not uinput:
            continue  # if null input
        if uinput == 'exit':
            print('Quitting...')
            loco_signal.put_nowait(None)
            broker_signal.put_nowait(None)
            bos_signal.put_nowait(None)
            exit()
        else:
            try:
                eval(uinput)
            except Exception as e:
                print('Invalid Command ' + str(e))
