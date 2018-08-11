""" msg_broker.py - A message broker for Edge Message Protocol (EMP) messages.
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

    Notes: 
    + Data is not persistent - when broker execution is terminated, all
      unfetched msgs are lost.

    + For this demo/simulated implementation, we can assume minimal clients.
      Therefore no session management is performed - TCP/IP connections are
      created and torn down each time a msg is sent or fetched.

    Author:
        Dustin Fast, 2018
"""
import socket
from ConfigParser import RawConfigParser
from time import sleep
from threading import Thread
from msg_lib import Message, MsgQueue
from lib import REPL

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

# TODO: Symbolic constants
OK = 'OK'
READY = 'READY'
FAIL = 'FAIL'
EMPTY = 'EMPTY'

class Broker(object):  # TODO: test mp?
    """ The message broker.
    """
    def __init__(self):
        """ Instantiates a message broker object.
        """
        # Dict of outgoing msg queues, by address: { dest_addr: MsgQueue }
        # Example: { 'sim.l.7357': MsgQueue }
        self.outgoing_queues = {}

        # On/Off flag for stopping threads. Set by self.start and self.stop.
        self.running = False

        # The msg receiver thread
        self.msg_recvr = Thread(target=self._msgreceiver)
        
        # The fetch watcher thread
        self.fetch_watcher = Thread(target=self._fetchwatcher)

        # The queue parser thread
        self.queue_parser = Thread(target=self._queueparser)

    def start(self):
        """ Start the msg broker, i.e., the msg receiver, fetch watcher and
            queue parser threads. 
        """
        self.running = True
        self.msg_recvr.start()
        self.fetch_watcher.start()
        self.queue_parser.start()
        print('Broker: Listening for requests...')

    def stop(self):
        """ Stops the msg brokeri.e., the msg receiver, fetch watcher and
            queue parser threads. 
        """
        if self.running:
            self.running = False 
            self.msg_recvr.join(timeout=REFRESH_TIME)
            self.fetch_watcher.join(timeout=REFRESH_TIME)
        print('Broker: Stopped.')

    def _msgreceiver(self):
        """ Watches for incoming messages over TCP/IP on the interface and port 
            specified.
        """
        # Init TCP/IP listener
        # TOOD: Move to lib
        sock = socket.socket()
        sock.settimeout(REFRESH_TIME)
        sock.bind((BROKER, BROKER_RECV_PORT))
        sock.listen(1)

        while self.running:
            # Block until timeout or a send request is received
            try:
                conn, client = sock.accept()
            except:
                continue
            print ('Broker: Send request received from: ' + str(client))

            # Receive the msg from sender, responding with either OK or FAIL
            try:
                raw_msg = conn.recv(MAX_MSG_SIZE).decode()
                msg = Message(raw_msg.decode('hex'))
            except Exception as e:
                print('Broker: Msg recv failed due to ' + str(e))
                try:
                    conn.send('FAIL'.encode())
                    conn.close()
                except:
                    continue

                # Add msg to outgoing queue dict, keyed by dest_addr
                if not self.outgoing_queues.get(msg.dest_addr):
                    self.outgoing_queues[msg.dest_addr] = MsgQueue()
                self.outgoing_queues[msg.dest_addr].push(msg)
                logstr = 'Broker: Received msg from ' + msg.sender_addr + ' '
                logstr += 'for ' + msg.dest_addr
                print(logstr)

                # Ack success with sender and close connection
                try:
                    conn.send('OK'.encode())
                    conn.close()
                except:
                    continue

        # Do cleanup
        sock.close()

    def _fetchwatcher(self):
        """ Watches for incoming TCP/IP msg requests (i.e.: A loco or the BOS
            checking its msg queue) and serves messages as appropriate.
        """
        # Init listener
        sock = socket.socket()
        sock.settimeout(REFRESH_TIME)
        sock.bind((BROKER, BROKER_FETCH_PORT))
        sock.listen(1)

        while self.running:
            # Block until timeout or a send request is received
            try:
                conn, client = sock.accept()
            except:
                continue
            print ('Broker: Fetch request received from: ' + str(client))

            # Process the request, responding with either READY, EMPTY, OK
            # or FAIL.
            try:
                queue_name = conn.recv(MAX_MSG_SIZE).decode()
                print('Broker: ' + queue_name + ' fetch requested.')

                # Ensure queue exists and is not empty
                # TODO: Ensure success before removing msg from queue
                try:
                    msg = self.outgoing_queues[queue_name].pop()
                except:
                    # As far as the client is concerned, the queue is empty.
                    msg = None  # implicit, but defined here for clarity

                try:
                    if msg:
                        conn.send('READY'.encode())  # Signal READY to send
                        conn.send(msg.raw_msg.encode('hex'))  # Send msg
                    else:
                        conn.send('EMPTY'.encode())
                    conn.close()
                except:
                    continue
            except:
                continue

        # Do cleanup
        sock.close()
        
    def _queueparser(self):
        """ Parses self.outgoing_queues and discards expired messages.
        """
        while self.running:
            # TODO: Parse all msgs for TTL
            # while not g_new_msgs.is_empty():
            #     msg = g_new_msgs.pop()

            sleep(REFRESH_TIME)


if __name__ == '__main__':
    # Init broker
    broker = Broker()
    
    # Init the Read-Eval-Print-Loop and start it
    welcome = ('-- Loco Sim Message Broker --\nTry "help" for assistance.')
    repl = REPL(broker, prompt='Broker>> ')
    exit_cond = 'running == False'
    repl.set_exitcond(exit_cond, 'Cannot exit while running. Try "stop" first')
    repl.add_cmd('start', 'start()')
    repl.add_cmd('stop', 'stop()')
    repl.start()
