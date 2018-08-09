""" A message broker for Edge Message Protocol (EMP) messages. Messages
    received are enqueued for receipt by their intended recipient.
    Note: Data is not persistent - when broker execution is terminated, all
    enqueued msgs are lost.
    Note: This module uses multiprocessing, requiring seperate queues to 
    comunicate. Don't confuse ...

    The broker consists of 3 components:
        Message Receiver - Watchers for incoming messages over TCP/IP. Runs as
                            a multiprocessing.Process
        Request Watcher  - Watches for & manages incoming TCP/IP msg requests
                            (ex: A loco checking for msgs addressed to it).
                            Runs as a multiprocessing.Process
        Message Broker   - Manages message queues

    Message Specification:
        EMP V4 (specified in msg_spec/S-9354.pdf) with fixed-format messages 
        containing a variable-length header section.
        See README.md for implementation specific information.


    Author:
        Dustin Fast, 2018
"""

import Queue
import socket
import multiprocessing
from time import sleep
from msg_lib import Message

# TODO: Conf variables
MAX_RECV_TRIES = 3
MAX_RECV_HZ = 2
SEND_PORT = 18181
RECV_PORT = 18182

class MsgRecevier(multiprocessing.Process):
    """ Watches for incoming messages over TCP/IP on the host and port 
        specified. Assumes localhost if no host specified.
        Intended to be run as a multiprocess.Process. Received EMP msgs are
        equened in the multiprocessing.Queue given to constructor.
    """
    def __init__(self, host='localhost', port=RECV_PORT):
        """
        """  
        multiprocessing.Process.__init__(self)  # init parent
        self.server = socket.socket().bind((host, port))
        self.return_queue = multiprocessing.Queue()

    def run(self):
        """ Blocks until a message is received, enqueues it in return_queue,
            then does it all over again.
        """
        # Init listener. Note: Because we close all conns soon after
        # they're established, and we can assume minimal requests for this demo
        # implementation, we don't allow or handle concurrent connections.
        self.server.listen(1)
        print ('Listening...')  # debug

        while True:
            # Block until a client connects
            conn, client = self.server.accept()
            print ('Client connected: ' + str(client[0]))  # debug

            # Try MAX_RECV_TRIES to recv msg, responding with either 
            # 'OK', 'RETRY', or 'FAIL'
            recv_tries = 0
            while True:
                recv_tries += 1
                raw_msg = conn.recv(1024).decode()
                try:
                    msg = Message(raw_msg)
                except Exception as e:
                    print('Failed w/ ' + str(e) + ' on try ' + str(recv_tries))  # debug
                    if recv_tries < MAX_RECV_TRIES:
                        conn.send(str('RETRY').encode())
                        continue
                    else:
                        # conn.send(str('FAIL').encode())  #TODO: Dep?
                        break
                
                # Enqueue msg in return_queue and ack with sender
                self.return_queue.put_nowait(msg)
                conn.send(str('OK').encode())
                break

            # We're done with client connection, so close it.
            conn.close()

        # If here, an error likely occured    
        self.server.close()
        print('MsgRecevier closed.')  # debug
        

class MsgBroker(object):
    """ The message broker.
    """
    def __init__(self, host='localhost', port=RECV_PORT):
        """
        """
        self.message_queues = {}  # Dict of msg queues: { dest_addr: Message }

        # Init and start MsgRecevier
        self.msg_watcher = MsgRecevier(host, port)
        self.return_queue = self.msg_watcher.return_queue

    def start(self):
        """ Start the msg broker.
        """
        self.msg_watcher.start()

        # Wait for msgs and enqueue as necessary
        while True:
            try:
                msg = self.return_queue.get(timeout=10)
            except Queue.Empty:
                print('Msg queue empty. Waiting for new msgs...')
                sleep(1)
                continue

            # Enqueue msg in a queue labeled as the dest address. It will
            # sit there until somoene requests it (or the broker closes).
            if not self.message_queues.get(msg.dest_addr):
                self.message_queues[msg.dest_addr] = Queue.Queue()
            self.message_queues[msg.dest_addr].put_nowait(msg)


if __name__ == '__main__':
    pass
