""" sim_bos.py - The Back Office Server (BOS). Watches for locomotive status
    msgs addressed to it at the broker and updates itself based on thier
    content. Also accepts user commands from either the terminal or its web
    interface to control each locomotive.

    Author: Dustin Fast, 2018
"""

from lib import REPL
from time import sleep
from Queue import Empty
from threading import Thread
from ConfigParser import RawConfigParser

from msg_lib import Client

# Init conf
config = RawConfigParser()
config.read('conf.dat')

# Import conf data
BROKER = config.get('messaging', 'broker')
MAX_TRIES = config.get('misc', 'max_retries')
BROKER_SEND_PORT = int(config.get('messaging', 'send_port'))
BROKER_FETCH_PORT = int(config.get('messaging', 'fetch_port'))
MAX_MSG_SIZE = int(config.get('messaging', 'max_msg_size'))
REFRESH_TIME = float(config.get('misc', 'refresh_sleep_time'))
MSG_INTERVAL = int(config.get('messaging', 'msg_interval'))
BOS_EMP = config.get('messaging', 'bos_emp_addr')
LOCO_EMP_PREFIX = config.get('messaging', 'loco_emp_prefix')


class BOS(object):
    """ A Back Office Server.
    """
    def __init__(self):
        """
        """
        # On/Off flag for threads. Set by self.start and self.stop.
        self.running = False

        # Messaging client
        self.msg_client = Client(BROKER, BROKER_SEND_PORT, BROKER_FETCH_PORT)

        # Message receiver thread
        self.status_watcher = Thread(target=self._statuswatcher)

        # Flag denoting status of REPL
        self.repl_running = False
        
    def start(self, terminal=False):
        """ Start the BOS. I.e., the status watcher thread. If terminal, also
            starts the repl.
        """
        if not self.running:
            self.running = True
            self.status_watcher.start()

        if terminal and not self.repl_running:
            self.repl_running = True
            self._repl()
        else:
            print('BOS: Running.')

    def stop(self):
        """ Stops the BOS.
        """
        if self.running:
            # Signal stop to threads and join
            self.running = False
            self.status_watcher.join(timeout=REFRESH_TIME)

            # Redefine threads, to allow starting after stopping
            self.status_watcher = Thread(target=self._statuswatcher)

        print('BOS: Stopped.')

    def _statuswatcher(self):
        """ The status message watcher thread - watches for locomotive status
            messages addressed to it at the broker.
        """
        while self.running:
            # Fetch the next available msg, if any
            raw_msg = None
            try:
                raw_msg = self.msg_client.fetch_next_msg(BOS_EMP)
            except Empty:
                print('BOS: No msgs avaiable to fetch.')
            except Exception as e:
                print('BOS: Msg fetch failed due to: ' + str(e))

            # Process msg
            if raw_msg:
                try:
                    sender = raw_msg.sender_addr
                    print('BOS: Status received for loco ' + str(sender))
                    # TODO: process status msg
                    # content = raw_msg.payload
                except:
                    print('BOS: Malformed status msg recevied.')

            sleep(MSG_INTERVAL)

    def _repl(self):
        """ Blocks while watching for terminal input, then processes it.
        """
        # Init the Read-Eval-Print-Loop and start it
        welcome = '-- Loco Sim Back Office Server  --\n'
        welcome += "Try 'help' for a list of commands."
        repl = REPL(self, 'BOS>> ',)
        repl.add_cmd('start', 'start()')
        repl.add_cmd('stop', 'stop()')
        repl.set_exitcmd('stop')
        repl.start()


if __name__ == '__main__':
    # Start the bos in terminal mode
    bos = BOS()
    bos.start(terminal=True)
