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


class REPL(object):
    """ A dynamic Read-Eval-Print-Loop. I.e. A command line interface.
        Contains two predefined commands: help, and exit. Additional cmds may
        be added with add_cmd(). These additional cmds all operate on the object
        given as the context. 
        Note: Assumes all expressions provided are well-formed. 
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
        self.exit_conditions = {}
        self.commands = {'help': 'self._help()',
                         'exit': 'self._exit()'
                         }

    def start(self):
        """ Starts the REPL.
        """
        if self.welcome_msg:
            print(self.welcome_msg)
        while True:
            # TODO: readline
            uinput = raw_input(self.prompt)
            cmd = self.commands.get(uinput)

            # Process user input
            if not uinput:
                continue  # if null input
            if not cmd:
                print('Invalid command. Try "help".')
            else:
                # print('Trying: ' + cmd)  # debug
                eval(cmd)

    def add_cmd(self, cmd_txt, expression):
        """ Makes a command available via the REPL
                cmd_txt: Txt cmd entered by the user
                expression: A well-formed python expression string.
                            ex: 'print('Hello World)'
        """
        if cmd_txt == 'help' or cmd_txt == 'exit':
            raise ValueError('An internal cmd override was attempted.')
        self.commands[cmd_txt] = 'self.context.' + expression

    def set_exitcond(self, expression, error_string):
        """ Specifies what must be true, in the given context, before exit.
                expression: A well formed python expression.
                            ex: 'stopped == True'
                error_string: The error string to display on exit when
                              expression resolves to False
        """
        self.exit_conditions['self.context.' + expression] = error_string

    def _help(self):
        """ Outputs all available commands to the console, excluding 'help'.
        """
        cmds = [c for c in sorted(self.commands.keys()) if c != 'help']
        if cmds:
            print('Available commands:')
            print('\n'.join(cmds))
        else:
            print('No commands defined.')

    def _exit(self):
        """ Calls exit(). If set_exit_cond() was used, exits conditionally.
        """
        ok_to_exit = True
        for cond, errstr in self.exit_conditions.items():
            if not eval(cond):
                print(errstr)
                ok_to_exit = False
                break

        if ok_to_exit:
            exit()


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
