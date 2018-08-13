""" demo.py - Starts the necessary services and processes
    The Locomotive, Back Office Serverm, and Message Broker each exist in
     seperate processes.

    Author: Dustin Fast, 2018
"""

import time
# import lib
import lib
# import sim_broker
# import sim_bos
# import sim_loco
# import multiprocessing


# class #TODO: proc(multiprocessing.Process):
#     """ Starts a subprocess with the given object.
#         Assumes object.start() exists. .end()?
#     """
#     def __init__(self):
#         multiprocessing.Process.__init__(self)
#         self.obj = msg_broker.Broker()

#     def run(self):
#         self.obj.start()


if __name__ == '__main__':
    pass
    # Start msg broker
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

    # # Send test msg
    # client = msg_lib.Client()
    # client.send_msg(message)
    # time.sleep(1)
    # print('Test msg sent to broker')

    # # Try to fetch msg from the queue we just sent for
    # # TODO: try/catch
    # msg = client.fetch_next_msg(msg_dest)
    # print(msg.payload)
    # while True:
    #     uinput = raw_input('Demo >>')
    #     if not uinput:
    #         continue
    #     print('Trying: ' + uinput)  # debug
    #     eval(uinput)
