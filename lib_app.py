""" PTC-Sim's library of app-level classes.

    Author: Dustin Fast, 2018
"""

import logging
import logging.handlers
from subprocess import check_output
from ConfigParser import RawConfigParser

# Import conf data
config = RawConfigParser()
config.read('app_config.dat')

APP_NAME = config.get('application', 'app_name')
REFRESH_TIME = int(config.get('application', 'refresh_time'))
WEB_EXPIRE = int(config.get('application', 'web_expire'))

LOG_LEVEL = int(config.get('logging', 'level'))
LOG_SIZE = int(config.get('logging', 'max_file_size')) 
LOG_FILES = config.get('logging', 'num_files')

# Module level loggers, Declared here and defined at the end of this file.
track_log = None
broker_log = None
bos_log = None


class Logger(logging.Logger):
    """ An extension of Python's logging.Logger. Implements log file rotation
        and optional console output.
    """
    def __init__(self,
                 name,
                 console_output=False,
                 level=LOG_LEVEL,
                 num_files=LOG_FILES,
                 max_filesize=LOG_SIZE):
        """
        """
        self.level = 0
        self.parent = None
        # logging.Logger.__init__(self, name, level)

        # # Define output formats
        # log_fmt = '%(asctime)s - %(levelname)s @ %(module)s: %(message)s'
        # log_fmt = logging.Formatter(log_fmt + '')

        # # Init log file rotation
        # fname = 'logs/' + name + '.log'
        # rotate_handler = logging.handlers.RotatingFileHandler(fname,
        #                                                       max_filesize,
        #                                                       num_files)
        # rotate_handler.setLevel(level)
        # rotate_handler.setFormatter(log_fmt)
        # self.addHandler(rotate_handler)

        # if console_output:
        #     console_fmt = '%(asctime)s - %(levelname)s @ %(module)s:'
        #     console_fmt += '\n%(message)s'
        #     console_fmt = logging.Formatter(console_fmt)
        #     console_handler = logging.StreamHandler()
        #     console_handler.setLevel(level + 10)
        #     console_handler.setFormatter(console_fmt)
        #     self.addHandler(console_handler)
    def log(s):
        pass

def dep_install(module_name):
    """ Prompts user to install the given module. Application quits on deny.
    """
    install_str = 'pip install ' + module_name

    prompt = module_name + ' is required. '
    prompt += 'Install with "' + install_str + '"? (Y/n): '
    do_install = raw_input(prompt)  

    if do_install == 'Y':
        print('Installing... Please wait.')
        check_output(install_str)
        print('Success!\n')
    else:
        print('Exiting.')
        exit()


# Module level loggers, Defined here and declared at the top of this file
track_log = Logger('log_track', False)
broker_log = Logger('log_broker', False)
bos_log = Logger('log_bos', False)
