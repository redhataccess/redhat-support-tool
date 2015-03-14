# -*- coding: utf-8 -*-

#
# Copyright (c) 2012 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#           http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from collections import deque
from optparse import OptionParser, Option
from redhat_support_tool.helpers.confighelper import _
from redhat_support_tool.helpers.common import set_docstring
import cmd
import gettext
import itertools
import os
import redhat_support_tool.helpers.common as common
import shlex
import sys
import textwrap

__author__ = 'Keith Robertson <kroberts@redhat.com>'


class DisplayOption(object):
    '''
    A simple container class that holds the text to be displayed
    in a numbered menu and the name of the function that should
    be called when the user selects that numbered menu option.
    '''
    display_text = None
    function_name = None

    def __init__(self, display_text, function_name):
        self.display_text = display_text
        self.function_name = function_name


class ObjectDisplayOption(DisplayOption):
    '''
    A simple container class that holds the text to be displayed
    in a numbered menu and the name of the function that should
    be called when the user selects that numbered menu option.
    '''
    stored_obj = None

    def __init__(self, display_text, function_name, stored_obj):
        DisplayOption.__init__(self, display_text, function_name)
        self.stored_obj = stored_obj


class HiddenCommand(object):
    '''
    A marker interface for plug-ins that you do not want to show
    to the user.  Simply inherit from this class multiple-inhertance
    style
    '''
    def __init(self):
        pass


class Plugin(object):
    '''
    The base class for plugins.

   Attributes:
    plugin_name  The variable is used by redhat-support-tool
                 as the command which is displayed to the user.
                 Example: Setting 'plugin_name = foobar' will
                 create an executable command named 'foobar'.
                 Example:
                  Welcome to the Red Hat Support Tool.
                  Command (? for help): foobar
                  Command (? for help): help foobar


    _args        The positional arguments on the command line left over
                 from running OptionParser.  Should be used by
                 subclasses to see what the user supplied.
                 Example: addcomment -c 123456 positional_arguments_here

    _options     A dictionary containing the options that were supplied
                 by the user.
                 Example:  addcomment -c 123456 positional_arguments_here
                 results in _options = {'comment': '123456'}

    _line        The unaltered STDIN line from the user


    Methods to override:
     - get_usage (required)
     - get_desc (required)
     - get_epilog (required)
     - get_options (optional depending on your command)
     - validate_args (recommended)
     - postinit (optional)
     - non_interactive_action (required)
     - config_help
     - config-set-option
     - config-get-option
    '''

    plugin_name = None
    _line = None
    _args = None
    _parser = None
    _options = None

    def __init__(self):
        self._line = None
        self._args = None
        self._options = None
        self._init_parser()

    #
    # Methods subclasses should override
    #

    # Override this
    @classmethod
    def get_usage(cls):
        '''
        The usage statement that will be printed by OptionParser.

        Example:
            - %prog -c CASENUMBER [options] <comment text here>
        Important: %prog is a OptionParser built-in.  Use it!
        '''
        return 'OVERRIDE ME: Plugin::get_usage'

    # Override this
    @classmethod
    def get_desc(cls):
        '''
        The description statement that will be printed by OptionParser.

        Example:
            - 'Use the \'%s\' command to add a comment to a case.'\
             % cls.plugin_name
        '''
        return 'OVERRIDE ME: Plugin::get_desc'

    # Override this
    @classmethod
    def get_epilog(cls):
        '''
        The epilog string that will be printed by OptionParser.  Usually
        used to print an example of how to use the program.

        Example:
         Examples:
          - %s -c 12345678 Lorem ipsum dolor sit amet, consectetur adipisicing
          - %s -c 12345678
        '''
        return ''

    # Override this
    @classmethod
    def get_options(cls):
        '''
        Subclasses that need command line options should override this method
        and return an array of optparse.Option(s) to be used by the
        OptionParser.

        Example:
         return [Option("-f", "--file", action="store",
                        dest="filename", help='Some file'),
                 Option("-c", "--case",
                        action="store", dest="casenumber",
                        help='A case')]

         Would produce the following:
         Command (? for help): help mycommand

         Usage: mycommand [options]

         Use the 'mycommand' command to find a knowledge base solution by ID
         Options:
           -h, --help  show this help message and exit
           -f, --file  Some file
           -c, --case  A case
         Example:
          - mycommand -c 12345 -f abc.txt

        '''
        return None

    def parse_args(self, line):
        '''
        Use this method to parse the arguments supplied by the user.

        This method will parse the given arguments from STDIN via
        the OptionParser.  It will set _args, _options, and _line
        so that subclasses can use them to see what the user provided.
        '''
        if common.is_interactive():
            if line != None:
                self._args = shlex.split(line)
        else:
            self._args = sys.argv[2:]
        self._options, self._args = self._parser.parse_args(self._args)
        self._line = line
        self._options = vars(self._options)

    # Override this
    def validate_args(self):
        '''
        A helper method that will be called by the framework logic after the
        plugin has been instantiated and the args have been processed by
        the base class's OptionParser.  You should place any logic in here
        to test for the requisite number of arguments, etc.

        Throws:
         An exception if _args or _options lack the requisite amount of data
         for the command to operate.

        Returns:
         Nothing

        Example:
        if len(self._args) <= 0:
            msg = _("ERROR: %s requires a knowledge base solution ID. "
                    "Try \'help %s\' for more information.") % \
                        (self.plugin_name,
                         self.plugin_name)
            print msg
            raise Exception(msg)
        '''
        pass

    # Override this
    def postinit(self):
        '''
        This method is called immediately after the validate_args
        method.  The intent is to place logic in here that
        is executed *after* you know that you have the requisite
        args from the user but aren't ready to send anything to
        STDOUT yet.

        This is useful for subclasses that have interactive and
        non-interactive behavior and want to co-locate some init
        logic.
        '''
        pass

    # Override this
    def insert_obj(self, obj):
        '''
        This method should be called prior to validate_args, and can
        be used to inject an object from an ObjectDisplayOption by
        LaunchHelper.
        '''
        pass

    # Override this
    def non_interactive_action(self):
        '''
        This method will be called by redhat-support-tool when the user
        issues the command in a non-interactive mode.

        It will be called after the constructor, postinit, and validate_args.

        All plugin's should implement this method.

        Example:
         redhat-support-tool addcomment -c 12345 'Problem solved!'
        '''
        print 'OVERRIDE ME: Plugin::action'

    @classmethod
    def get_name(cls):
        """Returns the plugin's name as a string. This should return a
        lowercase string.
        """
        if cls.plugin_name:
            return cls.plugin_name
        return cls.__name__.lower()

    #
    # Methods related to OptionParser
    #
    @classmethod
    def _init_parser(cls):
        # Python 2.4 compatability check.
        if sys.version_info[:2] >= (2, 5):
            OptionParser.format_epilog = lambda self, formatter: self.epilog
            OptionParser.format_description = \
                lambda self, formatter: self.description
            cls._parser = OptionParser(usage=cls.get_usage(),
                                      description=cls.get_desc(),
                                      prog=cls.get_name(),
                                      epilog=cls.get_epilog())
        else:
            OptionParser.format_description = \
                lambda self, formatter: self.description
            cls._parser = OptionParser(usage=cls.get_usage(),
                                      description=cls.get_desc(),
                                      prog=cls.get_name())
        # Check to see if the subclass has any optparse.Options
        # for the OptionParser.
        if cls.get_options():
            cls._parser.add_options(cls.get_options())

        # OptionParser will annoyingly call sys.exit when parse_args
        # is called with an invalid set of options.  Clearly, this doesn't
        # work well in this context.  Hence, we override this behavior.
        setattr(cls._parser,
                'error',
                getattr(cls,
                        '_print_opt_parse_error'))

    @classmethod
    def _print_opt_parse_error(cls, msg):
        '''
        A utility function to override OptionParser's annoying
        habit of calling sys.exit on invalid parameters.
        '''
        print msg

    @classmethod
    def show_command_help(cls):
        '''
        This function will display OptionParser help for the command.
        '''
        cls._init_parser()
        cls._parser.print_help()
        if sys.version_info[:2] <= (2, 5) and cls.get_epilog() != "":
            print cls.get_epilog()

    #
    # Methods related to configuration options.
    #

    # Override this
    @classmethod
    def config_help(self):
        '''
        If your plugin stores any options that can be set by the user
        override this function and return a string containing the options,
        one per line, with the option name and a description, including
        any default values.

        Example:

        return " %-10s: %-67s\n" % ('url',
            _('The support services URL.  Default=%s') % self.DEFAULT_URL)

        '''
        return ''


class InteractivePlugin(Plugin, cmd.Cmd):
    '''
    A helper class for plug-ins that need an interactive sub-menu.

    Some plug-ins require an interactive sub-menu (see example 1).
    These plug-ins should inherit from this class and implement the methods
    marked by '# Override this'.  These classes should also
    override the similarly marked methods in Plugin.

    Plug-ins that are subclasses of InteractivePlugin will have their
    superclass's 'cmdloop' function called when the user is running
    redhat-support-tool interactively.  This will allow the user
    to select the options that you have provided.

    Methods to override:
     - get_sub_menu_options (requied)
     - get_intro_text (optional)
     - get_prompt_text (optional)
     - get_more_options (optional)

    Example 1:
     $ redhat-support-tool
    Welcome to the Red Hat Support Tool.
    Command (? for help): <-- This is the main menu
    Command (? for help): listcases

    Type the number of the case to view or 'e' to return to the main menu.
     0   [Closed]              This is just a test
     1   [Waiting on Red Hat]  Test case for strata
     Select a case: <-- This is a sub-menu
    '''
    DEFAULT_INTRO_TEXT = _('Make a selection or \'e\' '
                            'to return to the main menu.')
    DEFAULT_PROMPT = _('Selection: ')
    DEFAULT_END_OF_ENTRIES = _('End of options.')
    DEFAULT_PARTIAL_ENTRIES = _('%s of %s entries printed.'
                                ' Type \'m\' to see more, or \'r\' to start'
                                ' from the beginning again.')
    DEFAULT_MORE_ENTRIES_MAYBE = _('More entries may be available.'
                                   ' Type \'m\' to try and retrieve more.')

    intro_text = DEFAULT_INTRO_TEXT
    prompt = DEFAULT_PROMPT
    end_of_entries = DEFAULT_END_OF_ENTRIES
    partial_entries = DEFAULT_PARTIAL_ENTRIES
    more_entries_maybe = DEFAULT_MORE_ENTRIES_MAYBE

    _sub_menu_index = 1
    help_is_options = True
    opts_updated = False

    def __init__(self,
                 intro_text=DEFAULT_INTRO_TEXT,
                 prompt=DEFAULT_PROMPT):
        '''
        Arguments:
         intro_text  - Command specific intro-text which is used when the
                       sub-menu is displayed.
         prompt      - Command specific prompt(eg. Show case:, Select section:,
                       etc.)
        '''
        cmd.Cmd.__init__(self)
        Plugin.__init__(self)
        if intro_text == None or intro_text == self.DEFAULT_INTRO_TEXT:
            self.intro_text = self.get_intro_text()
        if prompt == None or prompt == self.DEFAULT_PROMPT:
            self.prompt = self.get_prompt_text()

    # Override this
    def get_sub_menu_options(self):
        '''
        Override this method to tell this base class what your sub-menu
        options are.

        Sub-class implementations should return a collections.deque containing
        DisplayOption objects.  Items are printed in the order in which they
        are added.

        Example 1:
         deque.append(DisplayOption('Display Option 1', 'function1')
         deque.append(DisplayOption('Display Option 2', 'function1')

         Produces:
          Make a selection or type 'e' to return to the main menu.
          0   Display Option 1
          1   Display Option 2
          Selection:

        Example 2: A sub-menu:
         $ redhat-support-tool
        Welcome to the Red Hat Support Tool.
        Command (? for help): <-- This is the main menu
        Command (? for help): listcases

        Type the number of the case to view or 'e' to return to the main menu.
         0   [Closed]              This is just a test
         1   [Waiting on Red Hat]  Test case for strata
         Select a case: <-- This is a sub-menu
        '''
        return None

    # Override this
    def get_intro_text(self):
        '''
        If you want to supply a sub-menu intro text (see example)
        other than the default and you don't want to supply it via
        the constructor.  Override this.

        Example:
        Command (? for help): listcases

        Select a case. <-- This is the submenu intro
         0   [Closed]              This is just a test
        '''
        return self.DEFAULT_INTRO_TEXT

    # Override this
    def get_prompt_text(self):
        '''
        If you want to supply custom a sub-menu prompt (see example)
        other than the default and you don't want to supply it via
        the constructor.  Override this.

        Example:
        Command (? for help): listcases

        Select a case.
         0   [Closed]              This is just a test
        Selection: <-- this is the prompt
        '''
        return self.DEFAULT_PROMPT

    # Override this
    # pylint: disable=W0613
    def get_more_options(self, num_options):
        '''
        If you want to support fetching of additional records for display
        in the submenu, override this method.

        If there are additional entries get_sub_menu_options() will be
        called to obtain the updated deque() object.

        Returns True if additional entries are available
        Returns False if unsupported, or no additional entries are available
        '''
        return False

    #
    # Nothing to override below this point
    #
    def _print_submenu(self):
        '''
        This method will call get_sub_menu_options an print them
        to stdout as a selectable list for the user. Generally,
        no need to override this.
        '''
        terminfo = common.get_terminfo()
        paginate = False
        display_opt_deque = self.get_sub_menu_options()
        currentpos = self._sub_menu_index
        moreresults = False

        # If we have terminal information available (i.e. interactive &
        # via a known terminal) calculate number of entries to return
        # in one screen.
        if terminfo:
            paginate = True
            termheight = terminfo[0]
            termwidth = terminfo[1]
        else:
            termheight = 24
            termwidth = 80

        # It seems strange to get the len of a str of a len, but we need
        # to, so we can get an accurate width of the index column.
        idx_width = len(str(len(display_opt_deque)))
        opt_width = termwidth - idx_width - 2

        # We need to work out the min & max size of the headers
        intro_prompt_size = common.get_linecount(termwidth, True,
                                                 self.intro_text) + \
                            common.get_linecount(termwidth, True,
                                                 self.prompt)
        min_header_size = intro_prompt_size + \
                          common.get_linecount(termwidth, False,
                                               self.partial_entries,
                                               self.more_entries_maybe,
                                               self.end_of_entries)
        max_header_size = intro_prompt_size + \
                          common.get_linecount(termwidth, False,
                                               self.partial_entries,
                                               self.more_entries_maybe,
                                               self.end_of_entries)

        if len(display_opt_deque) <= (currentpos + (termheight -
                                                    min_header_size)):
            # Prefetch some more results now
            moreresults = self.get_more_options(termheight - min_header_size)
            # If we are going to run out of options during this
            # _print_submenu call, or there will none left once we have
            # completed printing. Try and get more options from the plugin.
            display_opt_deque = self.get_sub_menu_options()

        # If we have reached the end of the list, remind the user
        # and return from the function.
        if (currentpos > len(display_opt_deque)):
            print self.end_of_entries
            return

        if paginate:
            lines_to_fill = termheight - max_header_size - 1
        else:
            lines_to_fill = sys.maxint

        iter_entries = list(itertools.islice(display_opt_deque,
                                             currentpos - 1, (lines_to_fill +
                                                              currentpos - 1)))

        outputbuff = []
        # Print intro text
        outputbuff.append(self.intro_text)

        for display_opt, idx in itertools.izip(iter_entries,
                                               itertools.count(currentpos)):
            if paginate:
                output = " % *s %-*s" % (idx_width, idx,
                                         opt_width, display_opt.display_text)
                output_wrapped = textwrap.wrap(output, termwidth,
                                               subsequent_indent=' ' *
                                                        (idx_width + 2))
                if (len(outputbuff) + len(output_wrapped) +
                    max_header_size) > termheight:
                    break
                else:
                    outputbuff.extend(output_wrapped)
                    self._sub_menu_index = idx + 1
            else:
                output = " % *s %-s" % (idx_width, idx,
                                        display_opt.display_text)
                outputbuff.append(output)

        for line in outputbuff:
            print line

        if (self._sub_menu_index <= len(display_opt_deque)):
            print self.partial_entries % (self._sub_menu_index - 1,
                                          len(display_opt_deque))
        elif ((self._sub_menu_index - 1) == len(display_opt_deque)
              and moreresults):
            print self.more_entries_maybe
        else:
            print self.end_of_entries

    #
    # Methods related to shell interaction.  Nothing to see here move
    # along please ;)
    #
    def _invalid(self, line):
        print _('%s is an invalid selection. Type \'help\' to see '
                'valid selections again.') % line

    def emptyline(self):
        '''
        Override the default implementation of emptyline so
        that the last command isn't repeated.
        '''
        return None

    def precmd(self, line):
        num = -1
        try:
            num = int(line)
        # pylint: disable=W0702
        except:
            line = str(line).strip()

        if line == 'e' or line == 'q':
            return 'EOF'
        elif (line == 'help') or \
             (line == '') or \
             (line == 'm') or \
             (line == 'r') or \
             (line == '?') or \
             (line.startswith('shell')) or \
             (line.startswith('!')):
            return line
        elif num <= len(self.get_sub_menu_options()) and num > 0:
            num = num - 1
            display_opt_deque = self.get_sub_menu_options()
            func = getattr(self, display_opt_deque[num].function_name)
            func(display_opt_deque[num])
            if self.opts_updated:
                self._sub_menu_index = 1
                self._print_submenu()
                self.opts_updated = False
            return ''
        else:
            self._invalid(line)
            return ''

    def do_help(self, line):
        if not line:
            # Help can either be the options from the submenu, or
            # a listing of docstrings from the help_???? methods
            if self.help_is_options:
                # Plugin is using the options from _print_submenu as help
                # reset index to 1, and print again.
                self._sub_menu_index = 1
                self._print_submenu()
            else:
                common.do_help(self)
        else:
            cmd.Cmd.do_help(self, line)

    def do_m(self, line):
        self._print_submenu()

    @set_docstring(_('Show more options if available.'))
    def help_m(self):
        print
        print '\n'.join([_('Prints additional results. '
                           'if available.')])

    def do_r(self, line):
        self._sub_menu_index = 1
        self._print_submenu()

    @set_docstring(_('Restart display of options.'))
    def help_r(self):
        print
        print '\n'.join([_('Restarts display of results from '
                           'the start.')])

    @set_docstring(_('Return to previous menu.'))
    def help_e(self):
        print
        print '\n'.join([_('Exit this subcommand shell. '
                           'CTRL-D and CTRL-C also work.')])

    @set_docstring(_('Return to previous menu.'))
    def help_q(self):
        print
        self.help_e()

    def do_EOF(self, line):
        # EOF (^D) doesn't start a new line, lets do that
        # so it looks better.
        print
        return 'EOF'

    def do_shell(self, line):
        output = os.popen(line).read()
        print output

    @set_docstring(_('Execute a shell command. You can also use \'!\''))
    def help_shell(self):
        print
        print '\n'.join(['shell COMMAND',
                         _('Execute a shell command. You can also use \'!\''),
                         _('Example:'),
                         ' shell ls',
                         ' !ls'])

    def default(self, line):
        if 'EOF' == str(line).strip():
            return True
