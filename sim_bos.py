""" sim_bos.py - The Back Office Server (BOS)

    Author: Dustin Fast, 2018
"""

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
        pass
        
    def start(self):
        pass
