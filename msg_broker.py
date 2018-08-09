""" msg_broker.py - A message broker for Edge Message Protocol (EMP) messages.
    Msgs received are enqued for receipt and dequed/served on request.

    The broker consists of 3 main components:
        MsgReceiver     - Watchers for incoming messages over TCP/IP. Runs as
                            a thread.
        RequestWatcher  - Watches for incoming TCP/IP msg requests (ex: A
                            loco checking its msgqueue), serving msgs as 
                            appropriate. Runs as a Thread.
        MsgBroker       - The public facing class, Manages the MsgReceiver, 
                            RequestWatcher, and outgoing message queues.

    Message Specification:
        EMP V4 (specified in msg_spec/S-9354.pdf) with fixed-format messages 
        containing a variable-length header section.
        See README.md for implementation specific information.

    Note: Data is not persistent - when broker execution is terminated, all
    enqued msgs are lost.

    Author:
        Dustin Fast, 2018
"""
from Queue import Queue
from socket import socket
from msg_lib import Message
from threading import Thread

# TODO: Conf variables
MAX_RECV_TRIES = 3
MAX_RECV_HZ = 2  # TODO: Recv hz
SEND_PORT = 18181
RECV_PORT = 18182
BROKER = 'localhost'
MAX_MSG_SIZE = 1024

# Global list of msgs waiting to be enqued in outgoing queues
new_messages = []

class _MsgReceiver(Thread):
    """ Watches for incoming messages over TCP/IP on the interface and port 
        specified.
        Instantiate then run as a thread with. obj.start().
    """
    def __init__(self):
        """ Instantiates a MsgReceiver object.
        """  
        Thread.__init__(self)  # init parent
        self.recevier = socket().bind((BROKER, RECV_PORT))

    def run(self):
        """ Called on _MsgReceiver.start(), blocks until a message is received,
            enqueues it in return_queue (the multiprocessing.Queue passed to 
            constructor, then does it all over again.
        """
        # Init listener. 
        self.recevier.listen(1)
        print ('Listening...')  # debug

        while True:
            # Block until a client connects
            conn, client = self.recevier.accept()
            print ('Client connected: ' + str(client[0]))  # debug
            # TODO: threading.Thread(target=client_handler, args=(conn,)).start()

            # Try MAX_RECV_TRIES to recv msg, responding with either 'OK',
            # 'RETRY', or 'FAIL'.
            recv_tries = 0
            while True:
                recv_tries += 1
                raw_msg = conn.recv(MAX_MSG_SIZE).decode()
                try:
                    msg = Message(raw_msg)
                except Exception as e:
                    print('Failed w/ ' + str(e) + ' on try ' + str(recv_tries))  # debug
                    if recv_tries < MAX_RECV_TRIES:
                        conn.send(str('RETRY').encode())
                        continue
                    else:
                        conn.send(str('FAIL').encode())
                        break
                
                # Enqueue msg in return_queue and ack with sender
                self.return_queue.put_nowait(msg)
                conn.send(str('OK').encode())
                break

            # We're done with client connection, so close it.
            conn.close()

        # If here, an error likely occured    
        self.recevier.close()
        print('MsgRecevier closed.')  # debug
        

class _RequestWatcher(Thread):
    """ Watches for incoming TCP/IP msg requests (i.e.: A loco or the BOS
        checking its msg queue) and serves msgs as appropriate.
        Runs as a thread.
    """
    def __init__(self):
        Thread.__init__(self)  # init parent
        """
        """

    def run(self):
        """
        """
        

class Broker(object):
    """ The message broker.
    """
    def __init__(self):
        """
        """
        self.outgoing_queues = {}  # Dict of msg queues: { dest_addr: Message }
        self.msg_recvr = _MsgReceiver()
        self.req_watcher = _RequestWatcher()

    def start(self):
        """ Start the msg broker, including the msg recevier subprocess
            and msg watcher thread.
        """
        global new_messages

        print('Starting msg receiver...')
        self.msg_recvr.start()
        print('Starting request watcher...')
        self.req_watcher.start()
        print('Broker running...')

        # Enqueue any msgs waiting to be enqued
        while True:
            for msg in new_messages:
                # Enqueue msg in a queue labeled as the dest address. It will
                # sit there until somoene requests it (or the broker closes).
                if not self.outgoing_queues.get(msg.dest_addr):
                    self.outgoing_queues[msg.dest_addr] = Queue()
                self.outgoing_queues[msg.dest_addr].put_nowait(msg)
