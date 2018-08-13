#!/usr/bin/env python
""" demo.py - Starts the necessary services and processes for the LocoSim.
    The Locomotive, Message Broker, and Back Office Server each exist in
     seperate processes.

    Author: Dustin Fast, 2018
"""

import time
import multiprocessing
from Queue import Empty


class _process(multiprocessing.Process):
    """ Starts the given component of loco_sim, either "loco", "broker", 
        or "bos", as a multiprocessing.Process.
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
            except Empty:
                pass


def start():
    # TODO: No log output to console for demo
    """ Start the LocoSim application, with each component existing in a 
        seperate process.
    """
    print('-- LocoSim --')
    print('Navigate to https://localhost/LocoSim for web interface.')
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
    

if __name__ == '__main__':
    start()

    # # Start msg broker
    # broker = sim_broker.Broker()
    # logger.error('Broker started')

    # # Define test msg
    # msg_type = 6000
    # msg_source = 'sim.l.7357'
    # msg_dest = 'sim.b'
    # payload = {'sent': 0, 'loco': 1111, 'speed': 22,
    #            'lat': 333, 'long': 444, 'base': 555}
    # sndmsg = msg_lib.Message((msg_type,
    #                           msg_source,
    #                           msg_dest,
    #                           payload))
