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
from random import randrange
from threading import Thread
    
from lib_app import bos_log, dep_install
from lib_messaging import Client, Queue
from lib_track import Track, Loco, Location
from lib_web import get_locos_table, get_status_map, get_tracklines, get_loco_connlines

from lib_app import APP_NAME, REFRESH_TIME
from lib_messaging import BROKER, SEND_PORT, FETCH_PORT, BOS_EMP

# Attempt to import 3rd party modules and prompt for install on fail
try:
    import flask
except:
    dep_install('flask')
try:
    import flask_login
except:
    dep_install('flask_login')
try:
    import flask_googlemaps
except:
    dep_install('flask_googlemaps')

# List of session vars modifiable from client-side js
PUBLIC_SESSVARS = ['time_icand']

# Init Flask
bos_web = flask.Flask(__name__)
bos_web.secret_key = 'PTC-Sim secret key'
login_manager = flask_login.LoginManager()
login_manager.init_app(bos_web)
login_manager.login_view = 'login'
flask_googlemaps.GoogleMaps(bos_web, key="AIzaSyAcls51x9-GhMmjEa8pxT01Q6crxpIYFP0")
bos_sessions = {}  # { BOS_ID: BOS_OBJ }


##############################
# Flask Web Request Handlers #
##############################

@bos_web.before_request
def before_request():
    """ Before each client request is processed, refresh the session and.
        If the session is new, instantiate a BOS for the client.
        Note: Each session gets its own BOS. This is for demo/sim purposes,
        so that each web client can have it's own "sandbox".
    """
    global bos_sessions

    # If session exists, great.
    try:
        if flask.session['bos_id']:
            print('Request from existing client received.')

    # Else, init a new BOS associated w/an ID & flag sess dirty so change is registered
    # This is necessary because the BOS itself is not serializable.
    except:
        # Generate 16 bit hex BOS ID, used to associate the BOS w/the session.
        bos_ID = "%016x" % randrange(65535)  # 16 bit hex

        # Init a new boss associated with the 16 bit ID
        bos_sessions[bos_ID] = BOS()
        bos_sessions[bos_ID].start()
        sleep(.5)  # Ample time to start

        # Associate session with it's BOS
        flask.session['bos_id'] = bos_ID
        flask.session.modified = True
        bos_log.info('New client session started.')
        

@bos_web.route('/' + APP_NAME)
def home():
    """ Serves home.html after instantiating the client's unique track instance.
    """
    try:
        bos = bos_sessions[flask.session['bos_id']]
    except:
        bos_log.error('Failed to associate bos with its requestor.')
        return 'Error getting BOS'

    # Get a fresh status map
    tracklines = get_tracklines(bos.track)
    status_map = get_status_map(bos.track, tracklines)

    return flask.render_template('home.html', status_map=status_map)


@bos_web.route('/_home_get_async_content', methods=['POST'])
def _home_get_async_content():
    """ Serves updated asynchronous content, the locos table and status map.
    """
    print('ASYNC')

    # Get the sessions associated BOSd
    bos = bos_sessions[flask.session['bos_id']]

    # Get pdated locos_table
    locos_table = get_locos_table(bos.track)

    # Get updated map lines
    tracklines = get_tracklines(bos.track)
    conn_lines = get_loco_connlines(bos.track)
    
    loco_name = flask.request.json['loco_name']  # 'Loco XXXX'
    
    if loco_name:
        loco = bos.track.locos[loco_name.replace('Loco ', '')]
        status_map = get_status_map(bos.track, tracklines, loco)
        return flask.jsonify(status_map=status_map.as_json(),
                             locos_table=locos_table,
                             loco_connlines=conn_lines.get(loco_name))
    else:
        status_map = get_status_map(bos.track, tracklines)
        return flask.jsonify(status_map=bos.status_map.as_json(),
                             locos_table=bos.locos_table)


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

class BOS(object):
    """ The Back Office Server. Consists of a messaging client and status
        watcher thread that fetches messages from the broker over TCP/IP, in
        addition to the web interface.
    """
    def __init__(self):
        self.track = Track()
        self.locos_table = {}
        self.status_maps = {}  # { None: all_locos_statusmap, loco.name: loco_statusmap }
        self.conn_lines = {}   # { TrackDevice.name: loco_statusmap }

        # Messaging client
        self.msg_client = Client(BROKER, SEND_PORT, FETCH_PORT)

        # Thread
        self.msgwatcher_thread = Thread(target=self._msgwatcher)
    
    def start(self):
        """ Starts the BOS threads. 
        """
        bos_log.info('BOS Starting...')
        self.msgwatcher_thread.start()

    def _msgwatcher(self):
        """ Checks for msg broker for new status msgs every REFRESH_TIME sec.
        """
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

        
# def _webupdater(track):
#     """ The web updater thread. Parses the BOS's local track object's
#         devices and updates the web output (HTML table, Google Earth/KMLs, 
#         etc.) accordingly.
#     """

#     # Update g_locos_table and main panel map
#     self.locos_table = get_locos_table(self.track)

#     # Get updated map lines
#     tracklines = get_tracklines(self.track)
#     self.conn_lines = get_loco_connlines(self.track)
#     maps = {}  # Temporary container, so we never serve incomplete map

#     for loco in self.track.locos.values():
#         maps[loco.name] = get_status_map(self.track, tracklines, loco)
#     maps[None] = get_status_map(self.track, tracklines)  

#     self.status_maps = maps

#     sleep(REFRESH_TIME)


if __name__ == '__main__':
    # Start the Back Office Server
    print('-- ' + APP_NAME + ': Back Office Server - CTRL + C quits --\n')
    sleep(.2)  # Ensure welcome statment outputs before flask output
    # bos = BOS().start(debug=True)
    bos_web.run(debug=True, use_reloader=False)  # Blocks until CTRL+C
