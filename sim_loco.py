""" loco_sim.py -
Simulates a locomotive traveling on a railroad track. 

The user may interact with this module via command line or the Back Office
Server. 

See README.md for more info.

Author:
    Dustin Fast, 2018
"""
import json
import ConfigParser
from time import sleep
from threading import Thread
from optparse import OptionParser
from math import degrees, radians, sin, cos, atan2
from sim_lib import print_err
from sim_lib import _Base, _Milepost

# Init constants from config file
try:
    config = ConfigParser.RawConfigParser()
    config.read('sim_conf.dat')

    TRACK_RAILS = config.get('loco', 'track_rails')
    TRACK_BASES = config.get('loco', 'track_bases')
    LOCO_START_DIR = config.get('loco', 'start_direction')
    LOCO_START_HEADING = config.get('loco', 'start_heading')
    LOCO_START_MP = config.get('loco', 'start_milepost')  
    LOCO_START_SPEED = float(config.get('loco', 'start_speed'))
    LOCO_SIM_REFRESH = int(config.get('loco', 'sim_refresh'))
except ConfigParser.NoSectionError:
    errstr = 'Error loading configuration file - Ensure sim_conf.dat exists '
    errstr += 'and contains necessary section headers.'
    raise Exception(errstr)
except ConfigParser.NoOptionError:
    errstr = 'Error reading configuration file - One or more required options '
    errstr += 'are missing.'
    raise Exception(errstr)
    
