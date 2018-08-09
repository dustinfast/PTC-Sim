""" demo.py - Starts the necessary services and processes
    The locomotive, bos, and msg broker all exist in seperate processes.

    Author: Dustin Fast, 2018
"""

import time
import msg_lib
# import msg_broker
# import sim_bos
# import sim_loco


if __name__ == '__main__':
    """
    """
    # Define test msg
    msg_type = 6000
    msg_source = 'sim.l.7357'
    msg_dest = 'sim.b'
    payload = {'sent': 0, 'loco': 1111, 'speed': 22, 'lat': 333, 'long': 444, 'base': 555}

    message = msg_lib.Message((msg_type,
                              msg_source,
                              msg_dest,
                              payload))

    # Send test msg
    sender = msg_lib.MsgSender()
    sender.send_msg(message)
    time.sleep(2)
    # Try to fetch msg from the queue we just sent for
    watcher = msg_lib.MsgWatcher()
    try:
        watcher.get_next(msg_dest)
    except:
        print('Msg queue empty... Too bad.')


# class proc(multiprocessing.Process):
#     """ Starts a subprocess with the given object.
#         Assumes object.start() exists. .end()?
#     """
#     def __init__(self):
#         multiprocessing.Process.__init__(self)
#         self.obj = msg_broker.Broker()

#     def run(self):
#         self.obj.start()