""" bos.py - The Back Office Server (BOS).

    Author: Dustin Fast, 2018
"""

from lib import REPL
from ConfigParser import RawConfigParser

# Init conf
config = RawConfigParser()
config.read('conf.dat')

# Import conf data
BROKER = config.get('messaging', 'broker')
MAX_TRIES = config.get('misc', 'max_retries')
BROKER_RECV_PORT = int(config.get('messaging', 'send_port'))
BROKER_FETCH_PORT = int(config.get('messaging', 'fetch_port'))
MAX_MSG_SIZE = int(config.get('messaging', 'max_msg_size'))
REFRESH_TIME = float(config.get('misc', 'refresh_sleep_time'))


class BOS(object):
    def __init__(self):
        self.running = False
        pass
        
    def start(self):
        pass

    def stop(self):
        pass


if __name__ == '__main__':
    # Init broker
    bos = BOS()

    # Init the Read-Eval-Print-Loop and start it
    welcome = ('-- Loco Sim Back Office Server  --\nTry "help" for assistance.')
    repl = REPL(bos, prompt='BOS>> ')
    exit_cond = 'running == False'
    repl.set_exitcond(exit_cond, 'Cannot exit while running. Try "stop" first')
    repl.add_cmd('start', 'start()')
    repl.add_cmd('stop', 'stop()')
    repl.start()
