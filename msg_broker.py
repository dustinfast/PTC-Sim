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
from time import sleep
import socket
from msg_lib import Message, MsgQueue
from threading import Thread

# TODO: Conf variables
MAX_RECV_TRIES = 3
MAX_RECV_HZ = 2  # TODO: Recv hz
RECV_PORT = 18182
BROKER = 'localhost'
MAX_MSG_SIZE = 1024

# Global queue of all msgs waiting for placement in outgoing queues by Broker
g_new_msgs = MsgQueue()

class _RequestWatcher(Thread):
    """ Watches for incoming TCP/IP msg requests (i.e.: A loco or the BOS
        checking its msg queue) and serves msgs as appropriate.
        Usage: Instantiate, then run as a thread with _RequestWatcher.start()
    """
    def __init__(self):
        """
        """
        Thread.__init__(self)  # init parent
        
    def run(self):
        """
        """
        print('Request Watcher: Started watching...')

        # TODO On msg request for a given queue, check the ttl in msg -
        # if expired, discard and try next msg. maybe add send time to Message class


class _MsgReceiver(Thread):
    """ Watches for incoming messages over TCP/IP on the interface and port 
        specified.
        Usage: Instantiate, then run as a thread with _MsgReceiver.start()
    """
    def __init__(self):
        """ Instantiates a MsgReceiver object.
        """  
        Thread.__init__(self)  # init parent

    def run(self):
        """ Called on _MsgReceiver.start(), blocks until a message is received, 
            processes it, 
        """
        global g_new_msgs
        # Init listener
        sock = socket.socket()
        sock.bind((BROKER, RECV_PORT))
        sock.listen(1)

        while True:
            # Block until a client connects
            print('Msg Receiver: Listening on ' + str(RECV_PORT) + '...')  # debug
            conn, client = sock.accept()
            print ('Msg Receiver: Connected to: ' + str(client[0]))  # debug

            # Try MAX_RECV_TRIES to recv msg, responding with either 'OK',
            # 'RETRY', or 'FAIL'.
            recv_tries = 0
            while True:
                recv_tries += 1
                raw_msg = conn.recv(MAX_MSG_SIZE).decode()
                try:
                    msg = Message(raw_msg.decode('hex'))
                except Exception as e:
                    errstr = 'Msg Receiver: Transfer failed due to ' + str(e)
                    if recv_tries < MAX_RECV_TRIES:
                        print(errstr + '... Will retry.')
                        conn.send(str('RETRY').encode())
                        continue
                    else:
                        print(errstr + '... Retries exhausted.')
                        conn.send(str('FAIL').encode())
                        break
                
                # Add msg to global new_msgs queue, then ack with sender
                g_new_msgs.push(msg)
                conn.send(str('OK').encode())
                break

            # We're done with client connection, so close it.
            conn.close()
            print('Msg Receiver: Closing after 1st msg receipt for debug')
            break  # debug

        # Do cleanup   
        sock.close()
        print('Msg Receiver: Closed.')  # debug
        

class Broker(object):  # TODO: test mp?
    """ The message broker.
    """
    def __init__(self):
        """
        """
        self.outgoing_queues = {}  # Dict of msg queues: { dest_addr: Message }
        self.msg_recvr = _MsgReceiver()
        self.req_watcher = _RequestWatcher()

    def run(self):
        """ Start the msg broker, including the msg receiver and msg watcher 
            threads.
        """
        global g_new_msgs

        # Start msg receiver and request watcher threads
        self.msg_recvr.start()
        self.req_watcher.start()

        for i in range(10):
            # Enqueue any msgs waiting to be enqued in a queue keyed by the 
            # dest address. A msg enqued this way will stay there until fetched
            # by a client.
            print('Broker: Parsing new msgs...')
            while not g_new_msgs.is_empty():
                msg = g_new_msgs.pop()
                if not self.outgoing_queues.get(msg.dest_addr):
                    self.outgoing_queues[msg.dest_addr] = MsgQueue()
                self.outgoing_queues[msg.dest_addr].push(msg)

                print('Enqued msg in outgoing queue: ' + msg.dest_addr)
            
            sleep(2)

        # Do cleanup
        print('MsgReceiver closed.')  # debug


if __name__ == '__main__':
    global on_flag
    on_flag = True
    broker = Broker()
    broker.run()
    print('Broker: Closed.')

