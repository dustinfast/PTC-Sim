""" demo.py - Starts the necessary services and processes
    The Locomotive, Back Office Serverm, and Message Broker each exist in
     seperate processes.

    Author: Dustin Fast, 2018
"""
import lib
import multiprocessing


class demo_process(multiprocessing.Process):
    """ Starts a subprocess for the loco_sim demo.
    """
    def __init__(self, module_name):
        multiprocessing.Process.__init__(self)
        self.module_name = module_name

    def run(self):
        if self.module_name == 'loco':
            import sim_loco as module
            self.obj = module.SimLoco()
        elif self.module_name == 'broker':
            import sim_broker as module
            self.obj = module.Broker()
        elif self.module_name == 'bos':
            import sim_bos as module
            self.obj = module.BOS
        else:
            raise ValueError(self.module_name)

        self.obj.start()

    def stop(self):
        self.obj.stop()


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

    print('-- Loco Sim Demo --\n')

    # Start demo procs
    loco_proc = demo_process('loco').start()
    broker_proc = demo_process('broker')
    bos_proc = demo_process('bos')

    

    # Init the Read-Eval-Print-Loop and start it
    # TODO: Use REPL class
    # while True:
    #     uinput = raw_input('LocoSim >> ' )

        # Process user input
        # if not uinput:
        #     continue  # if null input
        # if uinput == 'q':
            
        #     print('Invalid command. Try "help".')
        # else:
        #     eval(cmd)
    

    
