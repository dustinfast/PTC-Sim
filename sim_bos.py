#!/usr/bin/env python
""" The Back Office Server (BOS). Publishes the PTC Sim web interface
    via Flask and watches for locomotive status msgs addressed to it at the 
    broker. The web display is updated to reflect loco status, including Google
    Earth location mapping. Restricted track sections may also be communicated
    to each loco from the BOS.

    Author: Dustin Fast, 2018
"""

from time import sleep
from threading import Thread
from subprocess import check_output
from ConfigParser import RawConfigParser

from lib_app import Logger
from lib_msging import Client, Queue
from lib_track import Track, Loco, Milepost

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

# Flask defs
web = Flask(__name__)

@web.route('/ptc_sim')
def home():
    return render_template('home.html')


class BOS(object):
    """ The back office server. Consists of a messaging client and status
        watcher thread that fetches messages from the broker over TCP/IP.
    """
    def __init__(self):
        self.running = False  # State Flag
        self.log = None  # Logger (defined on self.start)
        self.track = Track()  # Track object instance

        # Messaging client
        self.msg_client = Client(BROKER, BROKER_SEND_PORT, BROKER_FETCH_PORT)

        # Message watcher thread
        self.status_watcher_thread = Thread(target=self._statuswatcher)

    def start(self, debug=False):
        """ Start the BOS. I.e., the status watcher thread and web interface.
        """
        self.log = Logger('log_bos')
        self.log.info('BOS Started.')
        
        self.running = True
        self.status_watcher_thread.start()

        web.run(debug=debug)  # Web interface, blocks until killed from console

        # Do shutdown
        print('\nQuitting... Please wait.')
        self.running = False
        self.status_watcher_thread.join(timeout=REFRESH_TIME)
        self.log.info('BOS stopped.')

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
                self.log.info('Msg queue empty.')
            except Exception as e:
                self.log.warn('Could not connect to broker.')

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

                    self.log.info('Processed status msg for loco ' + loco.ID)
                except KeyError as e:
                    self.log.error('Malformed status msg received: ' +
                                   str(msg.payload))

            sleep(REFRESH_TIME)


if __name__ == '__main__':
    # Start the Back Office Server
    print('-- PTC Sim: Back Office Server - Press CTRL + C to quit --\n')
    sleep(.2)  # Ensure print statment occurs before flask output
    bos = BOS().start(debug=True)
