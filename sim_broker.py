#!/usr/bin/env python
""" broker.py - A message broker for Edge Message Protocol (EMP) messages.
    Msgs received are enqued for receipt and dequed/served on request.

    The broker consists of 3 seperate threads:
        Msg Receiver    - Watchers for incoming messages over TCP/IP.
        Fetch Watcher   - Watches for incoming TCP/IP msg fetch requests (ex: A
                            loco checking its msgqueue), serving msgs as 
                            appropriate. Runs as a Thread.
        Queue Parser    - Parses each msg queue and discards expires msgs.

    Message Specification:
        EMP V4 (specified in msg_spec/S-9354.pdf) with fixed-format messages 
        containing a variable-length header section.
        See README.md for implementation specific information.

    Author: Dustin Fast, 2018
"""
import socket  
from time import sleep
from threading import Thread
from ConfigParser import RawConfigParser
from sim_lib import Queue, Message, REPL, logger  # Also sets socket timeout

# Init conf
config = RawConfigParser()
config.read('conf.dat')

# Import conf data
REFRESH_TIME = float(config.get('application', 'refresh_time'))
BROKER = config.get('messaging', 'broker')
SEND_PORT = int(config.get('messaging', 'send_port'))
FETCH_PORT = int(config.get('messaging', 'fetch_port'))
MAX_MSG_SIZE = int(config.get('messaging', 'max_msg_size'))


class Broker(object):
    """ The message broker.
    """
    def __init__(self):
        """ Instantiates a message broker object.
        """
        # Dict of outgoing msg queues, by dest address: { ADDRESS: Queue }
        self.outgoing_queues = {}

        # On/Off flags
        self.running = False
        self.repl_started = False

        # Threads
        self.msg_recvr_thread = Thread(target=self._msgreceiver)
        self.fetch_watcher_thread = Thread(target=self._fetchwatcher)

        # Flag denoting status of REPL
        self.repl_started = False

    def start(self, terminal=False):
        """ Start the message broker, i.e., the msg receiver and fetch watche
            threads. If terminal, also starts the REPL
        """
        if not self.running:
            self.running = True
            self.msg_recvr_thread.start()
            self.fetch_watcher_thread.start()

            if terminal and not self.repl_started:
                self.repl_started = True
                self._repl()
            else:
                logger.info('Broker running.')

    def stop(self):
        """ Stops the msg broker. I.e., the msg receiver and fetch watcher 
            threads. 
        """
        if self.running:
            # Signal stop to threads and join
            self.running = False
            self.msg_recvr_thread.join(timeout=REFRESH_TIME)
            self.fetch_watcher_thread.join(timeout=REFRESH_TIME)

            # Redefine threads, to allow starting after stopping
            self.msg_recvr_thread = Thread(target=self._msgreceiver)
            self.fetch_watcher_thread = Thread(target=self._fetchwatcher)

        logger.info('Broker stopped.')

    def _msgreceiver(self):
        """ Watches for incoming messages over TCP/IP on the interface and port 
            specified.
        """
        # Init TCP/IP listener
        # TOOD: Move to lib
        sock = socket.socket()
        # sock.settimeout(REFRESH_TIME)
        sock.bind((BROKER, SEND_PORT))
        sock.listen(1)

        while self.running:
            # Block until timeout or a send request is received
            try:
                conn, client = sock.accept()
            except:
                continue

            # Receive the msg from sender, responding with either OK or FAIL
            log_str = 'Incoming msg from ' + str(client[0]) + '. Result='
            try:
                raw_msg = conn.recv(MAX_MSG_SIZE).decode()
                msg = Message(raw_msg.decode('hex'))
                conn.send('OK'.encode())
                conn.close()
            except Exception as e:
                log_str += 'Msg recv failed due to ' + str(e)
                logger.error(log_str)
                try:
                    conn.send('FAIL'.encode())
                except:
                    pass
                conn.close()
                continue

            # Add msg to outgoing queue dict, keyed by dest_addr
            if not self.outgoing_queues.get(msg.dest_addr):
                self.outgoing_queues[msg.dest_addr] = Queue.Queue()
            self.outgoing_queues[msg.dest_addr].put(msg)
            log_str = 'Msg received from ' + msg.sender_addr + ' '
            log_str += 'for ' + msg.dest_addr
            logger.info(log_str)

        # Do cleanup
        sock.close()

    def _fetchwatcher(self):
        """ Watches for incoming TCP/IP msg requests (i.e.: A loco or the BOS
            checking its msg queue) and serves messages as appropriate.
        """
        # Init listener
        sock = socket.socket()
        sock.bind((BROKER, FETCH_PORT))
        sock.listen(1)

        while self.running:
            # Block until timeout or a send request is received
            try:
                conn, client = sock.accept()
            except:
                continue
            
            # Process the request
            log_str = 'Fetch request from ' + str(client[0]) + ' '
            try:
                queue_name = conn.recv(MAX_MSG_SIZE).decode()
                log_str += 'for ' + queue_name + '. Result='

                msg = None
                try:
                    msg = self.outgoing_queues[queue_name].get(timeout=.5)
                except:
                    log_str += 'Queue empty.'
                    conn.send('EMPTY'.encode())
                
                if msg:
                    conn.send(msg.raw_msg.encode('hex'))  # Send msg
                    log_str += 'Msg served.'

                logger.info(log_str)
                conn.close()
            except:
                continue

        # Do cleanup
        sock.close()

    def _repl(self):
        """ Blocks while watching for terminal input, then processes it.
        """
        # Init the Read-Eval-Print-Loop and start it
        welcome = '-- LocoBOSS: Message Broker  --\n'
        welcome += "Try 'help' for a list of commands."
        repl = REPL(self, '', welcome)
        repl.add_cmd('start', 'start()')
        repl.add_cmd('stop', 'stop()')
        repl.set_exitcmd('stop')
        repl.start()


if __name__ == '__main__':
    # Start the broker in terminal mode
    Broker().start(terminal=True)
