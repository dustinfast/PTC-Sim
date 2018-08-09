""" msg_broker.py - A message broker for Edge Message Protocol (EMP) messages.
    Msgs received are enqued for receipt and dequed/served on request.

    The broker consists of 3 main components:
        MsgReceiver     - Watchers for incoming messages over TCP/IP. Runs as
                            a thread.
        RequestWatcher  - Watches for incoming TCP/IP msg fetch requests (ex: A
                            loco checking its msgqueue), serving msgs as 
                            appropriate. Runs as a Thread.
        Broker          - The public interface. Manages the MsgReceiver, 
                            RequestWatcher, and outgoing message queues.

    Message Specification:
        EMP V4 (specified in msg_spec/S-9354.pdf) with fixed-format messages 
        containing a variable-length header section.
        See README.md for implementation specific information.

    Note: Data is not persistent - when broker execution is terminated, all
    unfetched msgs are lost.

    Note: For this simulation/demo implementation, we can assume a minimal load,
    therefore, no session management is performed - a connection to the broker
    must be created each time a msg is sent to, or fetched from, the broker.

    Author:
        Dustin Fast, 2018
"""
from time import sleep
import socket
from msg_lib import Message, MsgQueue
from threading import Thread

# TODO: Conf variables
MAX_TRIES = 3  # TODO: No max tries
REFRESH_HZ = 2  # TODO: Recv hz
BROKER_RECV_PORT = 18182
BROKER_FETCH_PORT = 18183
BROKER = 'localhost'
MAX_MSG_SIZE = 1024
        

class Broker(object):  # TODO: test mp?
    """ The message broker.
    """
    def __init__(self):
        """ Instantiates a message broker object.
        """
        # The msg receiver thread
        self.msg_recvr = Thread(target=self._msgreceiver())
        
        # The fetch watcher thread
        self.req_watcher = Thread(target=self._fetchwatcher())

        # The outgoing msg queues, keyed by address: { dest_addr: MsgQueue }
        self.outgoing_queues = {}

    def run(self):
        """ Start the msg broker, including the msg receiver and fetch watcher 
            threads. Also parses self.outgoing_queues and discards expired msg
            every s.
        """
        # Start msg receiver and request watcher threads
        self.msg_recvr.start()
        self.req_watcher.start()

        for i in range(10):
            # TODO: Parse all msgs for TTL
            # while not g_new_msgs.is_empty():
            #     msg = g_new_msgs.pop()

            sleep(2)

        # Do cleanup
        # TODO: Gracefully kill all threads
        print('Broker closed.')  # debug

    def _fetchwatcher(self):
        """ Watches for incoming TCP/IP msg requests (i.e.: A loco or the BOS
            checking its msg queue) and serve messages as appropriate.
        """
        # Init listener
        sock = socket.socket()
        sock.bind((BROKER, BROKER_FETCH_PORT))
        sock.listen(1)

        while True:
            # Block until a a fetch request is received
            print('Watching on ' + str(BROKER_FETCH_PORT) + '.')
            conn, client = sock.accept()
            
            print ('Fetch request received from: ' + str(client))

            # Try MAX_TRIES to process request, responding with 'OK' or 'EMPTY'
            recv_tries = 0
            while True:
                recv_tries += 1
                queue_name = conn.recv(MAX_MSG_SIZE).decode()
                print('' + queue_name + ' fetch requested.')

                # Ensure queue exists and is not empty
                # try:
                msg = self.outgoing_queues[queue_name].pop()
                # except Exception:
                #     conn.send('EMPTY'.encode())
                #     break

                conn.send('OK'.encode())
                conn.send(msg.raw_msg.encode('hex'))  # Send msg

                # Acck with sender
                conn.send('OK'.encode())
                break

            # We're done with client connection, so close it.
            conn.close()
            print('Closing after 1st msg fetched for debug')
            break  # debug

        # Do cleanup
        sock.close()
        print('Watcher Closed.')  # debug

    def _msgreceiver(self):
        """ Watches for incoming messages over TCP/IP on the interface and port 
            specified.
            Usage: Instantiate, then run as a thread with _MsgReceiver.start()
        """
        # Init TCP/IP listener
        sock = socket.socket()
        sock.bind((BROKER, BROKER_RECV_PORT))
        sock.listen(1)

        while True:
            # Block until a send request is received
            print('Listening on ' + str(BROKER_RECV_PORT) + '.')
            conn, client = sock.accept()
            print ('Snd request received from: ' + str(client))

            # Try MAX_TRIES to recv msg, responding with either 'OK',
            # 'RETRY', or 'FAIL'.
            recv_tries = 0
            while True:
                recv_tries += 1
                raw_msg = conn.recv(MAX_MSG_SIZE).decode()
                try:
                    msg = Message(raw_msg.decode('hex'))
                except Exception as e:
                    errstr = 'Transfer failed due to ' + str(e)
                    if recv_tries < MAX_TRIES:
                        print(errstr + '... Will retry.')
                        conn.send('RETRY'.encode())
                        continue
                    else:
                        print(errstr + '... Retries exhausted.')
                        conn.send('FAIL'.encode())
                        break

                # Add msg to global new_msgs queue, then ack with sender
                if not self.outgoing_queues.get(msg.dest_addr):
                    self.outgoing_queues[msg.dest_addr] = MsgQueue()
                self.outgoing_queues[msg.dest_addr].push(msg)
                print('Broker: Enqued outgoing msg for: ' + msg.dest_addr)

                conn.send('OK'.encode())
                break

            # We're done with client connection, so close it.
            conn.close()
            print('Closing after 1st msg received for debug')
            break  # debug

        # Do cleanup
        sock.close()
        print('Receiver Closed.')  # debug


if __name__ == '__main__':
    global on_flag
    on_flag = True
    broker = Broker()
    broker.run()
    print('end main')

