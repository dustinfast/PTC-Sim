#!/usr/bin/env python
""" The Back Office Server (BOS). Publishes the LocoBOSS website
    via Flask and watches for locomotive status msgs addressed to it at the 
    broker. The web display is updated to reflect loco status, including Google
    Earth location mapping. Speed/direction commands may also be issued to
    each loco.

    Author: Dustin Fast, 2018
"""
from time import sleep
from threading import Thread
from subprocess import check_output
from ConfigParser import RawConfigParser

from lib import Track, Loco, Milepost, Client, Queue, logger

# Attempt to import flask and prompt for install on fail
while True:
    try:
        from flask import Flask, render_template
        break
    except:
        prompt = 'Flask is required, install it? (Y/n): '
        install_pip = raw_input(prompt)

        if install_pip == 'Y':
            print('Installing... Please wait.')
            result = check_output('pip install flask')
            print('Success!')
        else:
            print('Exiting.')
            exit()

# Init conf
config = RawConfigParser()
config.read('config.dat')

# Import conf data
REFRESH_TIME = float(config.get('application', 'refresh_time'))
BROKER = config.get('messaging', 'broker')
BROKER_SEND_PORT = int(config.get('messaging', 'send_port'))
BROKER_FETCH_PORT = int(config.get('messaging', 'fetch_port'))
BOS_EMP = config.get('messaging', 'bos_emp_addr')


web = Flask(__name__)

@web.route('/LocoBOSS')
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

        # Track object instance
        self.track = Track()

        # Messaging client
        self.msg_client = Client(BROKER, BROKER_SEND_PORT, BROKER_FETCH_PORT)

        # Message watcher thread
        self.status_watcher_thread = Thread(target=self._statuswatcher)

    def start(self, debug=False):
        """ Start the BOS. I.e., the status watcher thread and web interface.
        """
        logger.info('BOS Started.')
        
        self.running = True
        self.status_watcher_thread.start()

        # Start serving web interface. Blocks until killed by console.
        web.run(debug=debug)
        
        # Do shutdown
        print('\nQuitting... Please wait.')
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
                logger.info('Msg queue empty.')
            except Exception as e:
                logger.error('Fetch failed - connection error.')

            # Process loco status msg
            if msg:
                try:
                    locoID = msg.payload['loco']
                    milepost = Milepost(msg.payload['milepost'],
                                        msg.payload['lat'],
                                        msg.payload['long'])

                    baseIDs = eval(msg.payload['bases'])
                    bases = [self.track.bases.get(b) for b in baseIDs]

                    # Update the loco object
                    loco = self.track.locos.get(locoID)
                    if not loco:
                        loco = Loco(locoID)

                    loco.update(msg.payload['speed'],
                                msg.payload['heading'],
                                msg.payload['direction'],
                                milepost,
                                msg.payload['base'],
                                bases)

                    logger.info('Processed status msg for loco ' + loco.ID)
                except KeyError as e:
                    logger.error('Malformed status msg received: ' +
                                 str(msg.payload))

            sleep(REFRESH_TIME)

        # TODO: def _contentbuilder(self):
        #     """ Updates the web datatables.
        #     """


if __name__ == '__main__':
    # Start the Back Office Server
    print('-- LocoBOSS: Back Office Server')
    print('-- Press CTRL + C to quit')
    sleep(.2)  # Allow print statment to occur before flask output
    bos = BOS().start(debug=True)
