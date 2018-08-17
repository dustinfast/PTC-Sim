""" PTC Sim's library of common "app level" classes.

    Author: Dustin Fast, 2018
"""

import logging
import logging.handlers
from ConfigParser import RawConfigParser

# Init conf
config = RawConfigParser()
config.read('config.dat')

# Import conf data
REFRESH_TIME = int(config.get('application', 'refresh_time'))
LOG_LEVEL = int(config.get('logging', 'level'))
LOG_FILES = config.get('logging', 'num_files')
LOG_SIZE = int(config.get('logging', 'max_file_size')) 


class REPL(object):
    """ A dynamic Read-Eval-Print-Loop. I.e., a command line interface.
        Contains two predefined commands: help, and exit. Additional cmds may
        be added with add_cmd(). These additional cmds all operate on the 
        object instance given as the context.
    """

    def __init__(self, context, prompt='>>', welcome_msg=None):
        """ Instantiates an REPL object.
            context: The object all commands operate on.
            prompt: The REPL prompt.
            welcome: String to display on REPL start.
        """
        self.context = context
        self.prompt = prompt
        self.welcome_msg = welcome_msg
        self.exit_command = None
        self.commands = {'help': 'self._help()',
                         'exit': 'self._exit()'}

    def start(self):
        """ Starts the REPL.
        """
        if self.welcome_msg:
            print(self.welcome_msg)
        while True:
            uinput = raw_input(self.prompt)
            cmd = self.commands.get(uinput)

            if not uinput:
                continue  # if null input
            if not cmd:
                print('Invalid command. Try "help".')
            else:
                eval(cmd)

    def add_cmd(self, cmd_txt, expression):
        """ Makes a command available via the REPL. Accepts:
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
        exit()


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
        rotate_handler = logging.handlers.RotatingFileHandler(name + '.log',
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
