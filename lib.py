""" sim_lib.py - A collection of classes and helpers for the simulator

    Author:
        Dustin Fast, 2018
"""

###########
# Classes #
###########

class Milepost:
    """ An abstraction of a milepost.
        self.mp = (Float) The numeric milepost
        self.lat = (Float) Latitude of milepost
        self.long = (Float) Longitude of milepost
    """
    def __init__(self, mp, latitude, longitude):
        self.mp = mp
        self.lat = latitude
        self.long = longitude

    def __str__(self):
        """ Returns a string representation of the milepost """
        return str(self.mp)


class Base:
    """ An abstraction of a base station, including it's coverage area
        self.ID = (String) The base station's unique identifier
        self.coverage_start = (Float) Coverage start milepost
        self.coverage_end = (Float) Coverage end milepost
    """
    def __init__(self, baseID, coverage_start, coverage_end):
        self.ID = baseID
        self.cov_start = coverage_start
        self.cov_end = coverage_end

    def __str__(self):
        """ Returns a string representation of the base station """
        return self.ID

    def covers_mp(self, milepost):
        """ Given a milepost, returns True if this base station provides 
            coverage at that milepost, else returns False.
        """
        return milepost >= self.cov_start and milepost <= self.cov_end


#############
# Functions #
#############

def print_err(errstr, trystr=None):
    """ Prints a formatted error string. 
        Ex: errstr = 'No action given', trystr = '( add | rm )'
    """
    print('ERROR: ' + errstr + '.')
    if trystr:
        print('Try: ' + trystr)
