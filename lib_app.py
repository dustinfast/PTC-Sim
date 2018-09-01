""" PTC-Sim's library of common app-level classes.

    Author: Dustin Fast, 2018
"""

import logging
import logging.handlers
from subprocess import check_output
from ConfigParser import RawConfigParser

# Init conf
config = RawConfigParser()
config.read('config.dat')

# Import conf data
APP_NAME = config.get('application', 'app_name')
REFRESH_TIME = int(config.get('application', 'refresh_time'))

LOG_LEVEL = int(config.get('logging', 'level'))
LOG_SIZE = int(config.get('logging', 'max_file_size')) 
LOG_FILES = config.get('logging', 'num_files')

# Module level loggers, Declared here and defined at the end of this file.
track_log = None
broker_log = None
bos_log = None

class Prompt(object):
    """ A dynamic Read-Eval-Print-Loop. I.e., a command line interface.
        Contains two predefined commands: help, and exit. Additional cmds may
        be added with add_cmd(). These additional cmds all operate on the 
        object instance given as the context.
        # TODO: Support multiple contexts - See branch repl_w_objrefs
    """

    def __init__(self, context, prompt='>>', welcome_msg=None):
        """ Instantiates an Prompt object.
            context: The object all commands operate on.
            prompt: The Prompt prompt.
            welcome: String to display on Prompt start.
        """
        self.running = False  # kill flag
        self.context = context
        self.prompt = prompt
        self.welcome_msg = welcome_msg
        self.exit_command = None
        self.commands = {'help': 'self._help()',
                         'exit': 'self._exit()'}

    def start(self):
        """ Starts the Prompt.
        """
        self.running = True
        if self.welcome_msg:
            print(self.welcome_msg)
        while self.running:
            uinput = raw_input(self.prompt)
            cmd = self.commands.get(uinput)

            if not uinput:
                continue  # if empty input received
            if not cmd:
                print('Invalid command: "' + str(uinput) + '". Try "help".')
            else:
                eval(cmd)

        self.running = False

    def get_repl(self):
        """ Returns an instance of self with predefined start cmd, stop cmd, 
            and exit conditions.
            Assumes context has start() and stop() members.
            After calling get_repl, start the repl with Prompt.start()
        """
        repl = Prompt(self.context, '')
        repl.add_cmd('start', 'start()')
        repl.add_cmd('stop', 'stop()')
        repl.set_exitcmd('stop')
        return repl

    def add_cmd(self, cmd_txt, expression):
        """ Makes a command available via the Prompt. Accepts:
                cmd_txt: Txt cmd entered by the user.
                expression: A well-formed python statment. Ex: 'print('Hello)'
        """
        if cmd_txt == 'help' or cmd_txt == 'exit':
            raise ValueError('An internal cmd override was attempted.')
        self.commands[cmd_txt] = 'self.context.' + expression

    def set_exitcmd(self, cmd):
        """ Specifies a command to run on exit. 
        """
        self.exit_command = cmd

    def _help(self):
        """ Outputs all available commands to the console, excluding 'help'.
        """
        cmds = [c for c in sorted(self.commands.keys()) if c != 'help']

        print('Available commands:')
        print('\n'.join(cmds))

    def _exit(self):
        """ Calls exit() after doing self.exit_command (if defined).
        """
        if self.exit_command:
            eval(self.commands[self.exit_command])
        self.running = False

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
        logging.Logger.__init__(self, name, level)

        # Define output formats
        log_fmt = '%(asctime)s - %(levelname)s @ %(module)s: %(message)s'
        log_fmt = logging.Formatter(log_fmt + '')

        # Init log file rotation
        fname = 'logs/' + name + '.log'
        rotate_handler = logging.handlers.RotatingFileHandler(fname,
                                                              max_filesize,
                                                              num_files)
        rotate_handler.setLevel(level)
        rotate_handler.setFormatter(log_fmt)
        self.addHandler(rotate_handler)

        if console_output:
            console_fmt = '%(asctime)s - %(levelname)s @ %(module)s:'
            console_fmt += '\n%(message)s'
            console_fmt = logging.Formatter(console_fmt)
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level + 10)
            console_handler.setFormatter(console_fmt)
            self.addHandler(console_handler)

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
track_log = Logger('log_track', True)
broker_log = Logger('log_broker', True)
bos_log = Logger('log_bos', True)
