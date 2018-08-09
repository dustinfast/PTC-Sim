""" demo.py - Starts the necessary services and processes
    The locomotive, bos, and msg broker all exist in seperate processes.
"""

import msg_lib
import sim_bos
import sim_loco
import msg_broker
from multiprocessing import Process


class locosim_thread(Process):
    """ The Locomotive Simulator process.
    """
    def __init__(self):
        Process.__init__(self)
        self.locosim = sim_loco.start

    def run(self):
        self.locosim()


class broker_thread(Process):
    """ The Message Broker process.
    """
    def __init__(self):
        Process.__init__(self)
        self.msg_broker = msg_broker.Broker()

    def run(self):
        self.msg_broker.start()


class bos_thread(Process):
    """ The Message Broker process.
    """
    def __init__(self):
        Process.__init__(self)
        self.bos = sim_bos.BOS()

    def run(self):
        self.bos.start()




if __name__ == '__main__':
    # try:
    #     pass
    # TODO: except KeyboardInterrupt:
    #     # do graceful shutdown
    #     pass

    # Define test msg
    msg_type = 6000
    msg_source = 'sim.l.7357'
    msg_dest = 'sim.b'
    payload = {0, 1111, 22, 333, 444, 555}

    message = msg_lib.Message(msg_type,
                              msg_source,
                              msg_dest,
                              payload)

    # Start the msg broker
    broker = broker_thread()
    broker.start()

    # Start the loco sim
    loco = loco_sim

