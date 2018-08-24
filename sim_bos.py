#!/usr/bin/env python
""" PTC-Sim's Back Office Server (BOS). 
    Publishes the PTC-Sim web interface via Flask and watches the message
    broker (via TCP/IP) for device and locomotive status msgs. The web display 
    is then updated to reflect these statuses, including Google Earth location
    mapping. 
    The BOS may also also send outgoing computer-aided-dispatch (CAD) msgs to
    each device.

    Author: Dustin Fast, 2018
"""

from time import sleep
from threading import Thread
from subprocess import check_output

from flask_googlemaps import GoogleMaps

from lib_web import get_locos_table, get_status_map
from lib_app import bos_log
from lib_msging import Client, Queue
from lib_track import Track, Loco, Location

from lib_app import APP_NAME, REFRESH_TIME
from lib_msging import BROKER, SEND_PORT, FETCH_PORT, BOS_EMP

# Attempt to import flask and prompt for install on fail
while True:
    try:
        from flask import Flask, render_template, jsonify
        break
    except:
        prompt = 'Flask is required. Run "pip install flask"? (Y/n): '
        install_pip = raw_input(prompt)

        if install_pip == 'Y':
            print('Installing... Please wait.')
            result = check_output('pip install flask')
            print('Success!')
        else:
            print('Exiting.')
            exit()


#################
# Flask Web app #
#################

# Web state vars
locos_table = 'Error populating table.'
panel_map = 'Error populating overview.'
main_panels = {}  # { None: loco-free-panel, loco_id: panel, ... }
curr_loco = 'ALL'

# Init Flask Web Handler and Google Maps Flask module
bos_web = Flask(__name__)
GoogleMaps(bos_web, key="AIzaSyAcls51x9-GhMmjEa8pxT01Q6crxpIYFP0")


@bos_web.route('/' + APP_NAME)
def home():
    return render_template('home.html',
                           panel_map=panel_map)


@bos_web.route('/_home_locotable_update', methods=['GET'])
def _home_locotable_update():
    return jsonify(locos_table=locos_table)


@bos_web.route('/_home_map_update', methods=['GET'])
def _home_map_update():
    return jsonify(status_map=panel_map.as_json())

# @bos_web.route('/_home_select_loco', methods=['POST'])
# def _home_select_loco():
#     curr_loco = 


#############
# BOS Class #
#############

class BOS(object):
    """ The Back Office Server. Consists of a messaging client and status
        watcher thread that fetches messages from the broker over TCP/IP, in
        addition to the web interface.
    """
    def __init__(self):
        self.track = Track()    # Track object instance

        # Messaging client
        self.msg_client = Client(BROKER, SEND_PORT, FETCH_PORT)

        # Threading
        self.running = False  # Thread kill flag
        self.msg_watcher_thread = Thread(target=self._statuswatcher)
        self.webupdate_thread = Thread(target=self._webupdater)

    def start(self, debug=False):
        """ Start the BOS. I.e., the status watcher thread and web interface.
        """
        bos_log.info('BOS Starting.')
        
        self.running = True
        self.msg_watcher_thread.start()
        self.webupdate_thread.start()

        bos_web.run(debug=True, use_reloader=False)  # Blocks until CTRL+C

        # Do shutdown
        print('\nBOS Stopping... Please wait.')
        self.running = False
        self.msg_watcher_thread.join(timeout=REFRESH_TIME)
        self.webupdate_thread.join(timeout=REFRESH_TIME)
        bos_log.info('BOS stopped.')

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
                bos_log.info('Msg queue empty.')
            except Exception:
                bos_log.warn('Could not connect to broker.')

            # Process loco status msg. Msg should be of form given in 
            # docs/app_messaging_spec.md, Msg ID 6000.
            if msg and msg.msg_type == 6000:
                try:
                    locoID = msg.payload['loco']
                    location = Location(msg.payload['milepost'],
                                        msg.payload['lat'],
                                        msg.payload['long'])
                    active_conns = eval(msg.payload['conns'])  # evals to dict
                    # Reference (or instantiate) the loco object with given ID
                    loco = self.track.locos.get(locoID)
                    if not loco:
                        print('+++ new loco: ' + locoID)
                        loco = Loco(locoID, self.track)

                    # Update the BOS's loco object with status msg params
                    loco.update(msg.payload['speed'],
                                msg.payload['heading'],
                                msg.payload['direction'],
                                location,
                                msg.payload['bpp'],
                                active_conns)

                    # Update the last seen time for this loco
                    self.track.set_lastseen(loco)
                    
                    bos_log.info('Processed status msg for ' + loco.name)
                except KeyError:
                    bos_log.error('Malformed status msg: ' + str(msg.payload))
            elif msg:
                bos_log.error('Fetched unhandled msg type: ' + str(msg.msg_type))
                
            sleep(REFRESH_TIME)
        
    def _webupdater(self):
        """ The web updater thread. Parses the BOS's local track object's
            devices and updates the web output (HTML table, Google Earth/KMLs, 
            etc.) accordingly.
        """
        global locos_table, panel_map

        while self.running:
            # Update locos_table and main panel map
            locos_table = get_locos_table(self.track)
            panel_map = get_status_map(self.track, curr_loco)

            sleep(REFRESH_TIME)


if __name__ == '__main__':
    # Start the Back Office Server
    print('-- ' + APP_NAME + ': Back Office Server - CTRL + C quits --\n')
    sleep(.2)  # Ensure print statment occurs before flask output
    bos = BOS().start(debug=True)
