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
from datetime import timedelta
from random import randrange
from threading import Thread
    
from lib_messaging import Client, Queue
from lib_app import bos_log, dep_install
from lib_track import Track, Loco, Location
from lib_web import get_locos_table, get_status_map, get_tracklines, get_loco_connlines

from lib_app import APP_NAME, REFRESH_TIME, WEB_EXPIRE
from lib_messaging import BROKER, SEND_PORT, FETCH_PORT, BOS_EMP

# Attempt to import 3rd party modules and prompt for install on fail
try:
    import flask
except:
    dep_install('flask')
try:
    import flask_googlemaps
except:
    dep_install('flask_googlemaps')

# List of session vars modifiable from client-side js
PUBLIC_SESSVARS = ['time_icand']

# Init Flask
bos_web = flask.Flask(__name__)
bos_web.secret_key = 'PTC-Sim secret key'
flask_googlemaps.GoogleMaps(bos_web, key="AIzaSyAcls51x9-GhMmjEa8pxT01Q6crxpIYFP0")
bos_sessions = {}  # { BOS_ID: BOS_OBJ }


##############################
# Flask Web Request Handlers #
##############################

@bos_web.before_request
def before_request():
    """ Before each client request is processed, refresh the session.
        If the session is new, instantiate a BOS for the client.
        Note: Each session gets its own BOS. This is for demo/sim purposes,
        so that each web client can have it's own "sandbox" BOS.
    """
    global bos_sessions
    
    def refresh_sess():
        bos_web.permanent_session_lifetime = timedelta(minutes=WEB_EXPIRE)
        flask.session.permanent = True
        flask.session.modified = True
    
    # If session exists, refresh it to prevent expire
    if flask.session.get('bos_id') and bos_sessions.get(flask.session['bos_id']):
        print('Request from existing client received.')
        refresh_sess()

    # Else, init a new BOS & flag session as dirty so change is registered.
    # The association is necessary because the BOS obj is not serializable.
    else:
        # Init a new boss associated with a random 16 bit ID
        bos_ID = randrange(65536)  
        bos_sessions[bos_ID] = BOS()
        bos_sessions[bos_ID].start()
        sleep(.5)  # Ample time to start

        # Associate session with it's BOS
        flask.session['bos_id'] = bos_ID
        refresh_sess()
        bos_log.info('New client session started: ' + str(bos_ID))
        

@bos_web.route('/' + APP_NAME)
def home():
    """ Serves home.html after instantiating the client's unique track instance.
    """
    try:
        bos = bos_sessions[flask.session['bos_id']]
    except:
        return 'BOS association failure. Try restarting your browser.'

    # Get a fresh status map
    tracklines = get_tracklines(bos.track)
    status_map = get_status_map(bos.track, tracklines)

    return flask.render_template('home.html', status_map=status_map)


@bos_web.route('/_home_get_async_content', methods=['POST'])
def _home_get_async_content():
    """ Serves updated asynchronous content, the locos table and status map.
    """
    # Get the session's associated BOS
    print('** ' + str(flask.session['bos_id']))
    bos = bos_sessions[flask.session['bos_id']]

    locos_table = get_locos_table(bos.track)
    tracklines = get_tracklines(bos.track)
    loco_name = flask.request.json['loco_name']  # 'Loco XXXX'

    if loco_name:
        loco = bos.track.locos[loco_name.replace('Loco ', '')]
        status_map = get_status_map(bos.track, tracklines, loco)
        conn_lines = get_loco_connlines(bos.track)  # TODO: get single line
        return flask.jsonify(locos_table=locos_table, 
                             status_map=status_map.as_json(),
                             loco_connlines=conn_lines.get(loco_name))
    else:
        status_map = get_status_map(bos.track, tracklines)
        return flask.jsonify(locos_table=locos_table,
                             status_map=status_map.as_json())


@bos_web.route('/_set_sessionvar', methods=['POST'])
def main_set_sessionvar_async():
    """ Accepts a key value pair via ajax and updates session[key] with the 
        given value. Key must be in PUBLIC_SESSVARS, for safety.
    """
    try:
        key = flask.request.json['key']
        newval = flask.request.json['value']

        if key in PUBLIC_SESSVARS:
            flask.session[key] = newval
            bos_log.info('Set: ' + key + '=' + newval)

        return 'OK'
    except Exception as e:
        bos_log.error(e)
        return 'error'


#############
# BOS Class #
#############

class BOS(Thread):
    """ The Back Office Server. Consists of a messaging client and status
        watcher thread that fetches messages from the broker over TCP/IP, in
        addition to the web interface.
    """
    def __init__(self):
        Thread.__init__(self)
        self.track = Track()
        self.msg_client = Client(BROKER, SEND_PORT, FETCH_PORT)

        # TODO: For demo purposes, each BOS gets it's own msg broker.

    def run(self):
        """ Checks msg broker for new status msgs every REFRESH_TIME sec.
        """
        bos_log.info('BOS Starting.')

        # TODO: For demo purposes, each BOS's track is also a Track Sim
        # for loco in self.track.locos.values():
        #     loco.sim.start()

        bos_log.info('BOS Started.')
        
        while True:
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

                    # Eiter reference or instantiate loco with the given ID
                    loco = self.track.locos.get(locoID)
                    if not loco:
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


if __name__ == '__main__':
    # Start the Back Office Server
    print('-- ' + APP_NAME + ': Back Office Server - CTRL + C quits --\n')
    sleep(.2)  # Ensure welcome statment outputs before flask output
    bos_web.run(debug=True, use_reloader=False)  # Blocks until CTRL+C
