#!/usr/bin/env python
""" sim_bos.py - The Back Office Server (BOS). Watches for locomotive status
    msgs addressed to it at the broker and updates itself based on thier
    content. Also accepts user commands from either the terminal or its web
    interface to control each locomotive.

    Author: Dustin Fast, 2018
"""

from time import sleep
from threading import Thread
from ConfigParser import RawConfigParser
from sim_lib import Loco, Client, Queue, REPL, logger

# Init conf
config = RawConfigParser()
config.read('conf.dat')

# Import conf data
REFRESH_TIME = float(config.get('application', 'refresh_time'))
BROKER = config.get('messaging', 'broker')
BROKER_SEND_PORT = int(config.get('messaging', 'send_port'))
BROKER_FETCH_PORT = int(config.get('messaging', 'fetch_port'))
BOS_EMP = config.get('messaging', 'bos_emp_addr')


class BOS(object):
    """ A Back Office Server.
    """
    def __init__(self):
        """
        """
        # On/Off flags.
        self.running = False
        self.repl_started = False

        # Messaging client
        self.msg_client = Client(BROKER, BROKER_SEND_PORT, BROKER_FETCH_PORT)

        # Message watcher thread
        self.status_watcher_thread = Thread(target=self._statuswatcher)

    def start(self, terminal=False):
        """ Start the BOS. I.e., the status watcher thread. If terminal, also
            starts the repl.
        """
        if not self.running:
            self.running = True
            self.status_watcher_thread.start()

            if terminal and not self.repl_started:
                self.repl_started = True
                self._repl()
            else:
                logger.info('BOS running.')

    def stop(self):
        """ Stops the BOS.
        """
        if self.running:
            # Signal stop to threads and join
            self.running = False
            self.status_watcher_thread.join(timeout=REFRESH_TIME)

            # Redefine threads, to allow starting after stopping
            self.status_watcher_thread = Thread(target=self._statuswatcher)

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
                logger.error('Msg fetch failed due to: ' + str(e))

            # TODO: Process loco status msg
            if msg:
                try:
                    # loco = Loco(msg.payload['loco'], msg)
                    # logger.info(str(loco))
                    logger.debug('Recvd status msg.')
                except KeyError as e:
                    logger.error('Malformed status msg received: ' + str(e))

            sleep(REFRESH_TIME)

    def _repl(self):
        """ Blocks while watching for terminal input, then processes it.
        """
        # Init the Read-Eval-Print-Loop and start it
        welcome = '-- Loco Sim Back Office Server  --\n'
        welcome += "Try 'help' for a list of commands."
        repl = REPL(self, 'BOS >> ', welcome)
        repl.add_cmd('start', 'start()')
        repl.add_cmd('stop', 'stop()')
        # TODO: Loco cmd msg
        repl.set_exitcmd('stop')
        repl.start()


if __name__ == '__main__':
    # Start the bos in terminal mode
    bos = BOS()
    bos.start(terminal=True)
