#!/usr/bin/env python
""" A message broker for Edge Message Protocol (EMP) messages.
    Msgs are received and enqued for receipt and dequed for recipient on
    request.

    Message Specification:
        EMP V4 (specified in msg_spec/S-9354.pdf) fixed-format messages 
        with variable-length header sections.
        See README.md for implementation specific information.

    Author: Dustin Fast, 2018
"""
import socket  
from threading import Thread
from ConfigParser import RawConfigParser

from lib_app import REPL, Logger
from lib_msging import Queue, Message

# Init conf
config = RawConfigParser()
config.read('config.dat')

# Import conf data
REFRESH_TIME = float(config.get('application', 'refresh_time'))
BROKER = config.get('messaging', 'broker')
SEND_PORT = int(config.get('messaging', 'send_port'))
FETCH_PORT = int(config.get('messaging', 'fetch_port'))
MAX_MSG_SIZE = int(config.get('messaging', 'max_msg_size'))

class Broker(object):
    """ The message broker. Consists of three seperate threads:
        Msg Receiver  - Watchers for incoming messages over TCP/IP.
        Fetch Watcher - Watches for incoming fetch requests over TCP/IP and
                        serves msgs as appropriate.
    """
    def __init__(self):
        # Dict of outgoing msg queues, by dest address: { ADDRESS: Queue }
        self.outgoing_queues = {}

        # State flags
        self.running = False
        self.terminal_started = False

        # Logger (defined on self.start)
        self.log = None

        # Threads
        self.msg_recvr_thread = Thread(target=self._msgreceiver)
        self.fetch_watcher_thread = Thread(target=self._fetchwatcher)

    def start(self, terminal=False):
        """ Start the message broker threads. If terminal, also starts the
            REPL and enables log output to console.
        """
        if not self.running:
            if not self.log:
                self.log = Logger('log_broker', terminal)
            self.log.info('Broker Started.')
            
            self.running = True
            self.msg_recvr_thread.start()
            self.fetch_watcher_thread.start()

            if terminal and not self.terminal_started:
                self.terminal_started = True
                self._repl()  # Blocks
            
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

            self.log.info('Broker stopped.')

    def _msgreceiver(self):
        """ Watches for incoming messages over TCP/IP on the interface and port 
            specified.
        """
        # Init TCP/IP listener
        sock = socket.socket()
        sock.bind((BROKER, SEND_PORT))
        sock.listen(1)

        while self.running:
            # Block until timeout or a send request is received
            try:
                conn, client = sock.accept()
            except:
                continue

            # Receive the msg from sender, responding with either OK or FAIL
            log_str = 'Incoming msg from ' + str(client[0]) + ' gave: '
            try:
                raw_msg = conn.recv(MAX_MSG_SIZE).decode()
                msg = Message(raw_msg.decode('hex'))
                conn.send('OK'.encode())
                conn.close()
            except Exception as e:
                log_str += 'Msg recv failed due to ' + str(e)
                self.log.error(log_str)

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
            log_str = 'Success - ' + msg.sender_addr + ' '
            log_str += 'to ' + msg.dest_addr
            self.log.info(log_str)

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
                log_str += 'for ' + queue_name + ' gave: '

                msg = None
                try:
                    msg = self.outgoing_queues[queue_name].get(timeout=.5)
                except:
                    log_str += 'Queue empty.'
                    conn.send('EMPTY'.encode())
                
                if msg:
                    conn.send(msg.raw_msg.encode('hex'))  # Send msg
                    log_str += 'Msg served.'

                self.log.info(log_str)
                conn.close()
            except:
                continue

        # Do cleanup
        sock.close()

    def _repl(self):
        """ Blocks while watching for terminal input, then processes it.
        """
        # Init the Read-Eval-Print-Loop and start it
        repl = REPL(self, '')
        repl.add_cmd('start', 'start()')
        repl.add_cmd('stop', 'stop()')
        repl.set_exitcmd('stop')
        repl.start()


if __name__ == '__main__':
    # Start the broker in terminal mode
    print("-- PTCSim: Message Broker - Type 'exit' to quit --\n")
    Broker().start(terminal=True)
