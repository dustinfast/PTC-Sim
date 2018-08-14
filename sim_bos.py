#!/usr/bin/env python
""" The Back Office Server (BOS). Publishes the LocoSim website
    via Flask and watches for locomotive status msgs addressed to it at the 
    broker. The web display is updated to reflect loco status, including Google
    Earth location mapping. Speed/direction commands may also be issued to
    each loco.

    Author: Dustin Fast, 2018
"""

from time import sleep
from threading import Thread
from ConfigParser import RawConfigParser

# Flask web interface
try:
    from flask import Flask, render_template
except:
    print('Flask is required - use "pip install flask" to install it.')
    exit()

from sim_lib import Client, Queue, logger

# Init conf
config = RawConfigParser()
config.read('conf.dat')

# Import conf data
REFRESH_TIME = float(config.get('application', 'refresh_time'))
BROKER = config.get('messaging', 'broker')
BROKER_SEND_PORT = int(config.get('messaging', 'send_port'))
BROKER_FETCH_PORT = int(config.get('messaging', 'fetch_port'))
BOS_EMP = config.get('messaging', 'bos_emp_addr')


bos_web = Flask(__name__)

@bos_web.route('/LocoSim')
def home():
    return render_template('home.html')


class BOS(object):
    """ A Back Office Server.
    """
    def __init__(self):
        """
        """
        # Thread on/off flag
        self.running = False
        # Messaging client
        self.msg_client = Client(BROKER, BROKER_SEND_PORT, BROKER_FETCH_PORT)

        # Message watcher thread
        self.status_watcher_thread = Thread(target=self._statuswatcher)

    def start(self, debug=False):
        """ Start the BOS. I.e., the status watcher thread and web interface.
        """
        self.running = True
        self.status_watcher_thread.start()
        logger.info('BOS Started.')

        # Start serving web interface. Blocks until killed by console.
        bos_web.run(debug=debug)
            
        # Do shutdown
        self.running = False
        self.status_watcher_thread.join(timeout=REFRESH_TIME)
        logger.info('BOS stopped.')

    def _statuswatcher(self):
        """ The status message watcher thread - watches the broker for msgs
            addressed to it and processes them.
        """
        while self.running:
            # Fetch the next available msg, if any
            msg = None
            try:
                msg = self.msg_client.fetch_next_msg(BOS_EMP)
            except Queue.Empty:
                logger.debug('Status msg queue empty.')
            except Exception as e:
                logger.error('Msg fetch failed - No response from broker.')

            # TODO: Process loco status msg
            if msg:
                try:
                    # loco = Loco(msg.payload['loco'], msg)
                    # logger.info(str(loco))
                    logger.debug('Recvd status msg.')
                except KeyError as e:
                    logger.error('Malformed status msg received: ' + str(e))

            sleep(REFRESH_TIME)


if __name__ == '__main__':
    # Start the Back Office Server
    print('-- LocoBOS: Back Office Server --')
    bos = BOS().start(debug=True)
