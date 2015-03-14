# -*- coding: utf-8 -*-

#
# Copyright (c) 2013 Red Hat, Inc.
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
from redhat_support_tool.helpers.confighelper import _
from redhat_support_tool.helpers.launchhelper import LaunchHelper
from redhat_support_tool.plugins import InteractivePlugin, ObjectDisplayOption
from redhat_support_tool.plugins.symptom import Symptom
import logging
import pydoc as pydoc
import redhat_support_tool.helpers.analyzer as analyzer
import redhat_support_tool.helpers.common as common
import redhat_support_tool.symptoms as Symptoms

__author__ = 'Dan Varga <dvarga@redhat.com>'

logger = logging.getLogger("redhat_support_tool.plugins.analyze")


class Analyze(InteractivePlugin):
    plugin_name = 'analyze'
    ALL = _("Analyze a file for symptoms")
    partial_entries = _('%s of %s symptoms displayed. Type \'m\' to see more.')
    end_of_entries = _('No more symptoms to display')
    _submenu_opts = None
    _sections = None
    filename = None
    results = None

    def __init__(self):
        InteractivePlugin.__init__(self)

    @classmethod
    def get_usage(cls):
        '''
        The usage statement that will be printed by OptionParser.

        Example:
            - %prog -c CASENUMBER [options] <comment text here>
        Important: %prog is a OptionParser built-in.  Use it!
        '''
        return _('%prog <file for analysis>')

    @classmethod
    def get_desc(cls):
        '''
        The description statement that will be printed by OptionParser.

        Example:
            - 'Use the \'%s\' command to add a comment to a case.'\
             % cls.plugin_name
        '''
        return _('Use the \'%s\' command to analyze a file for'
                 ' symptoms') % cls.plugin_name

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
        return _("Examples:\n"
                 "- %s /var/log/jbossas/rhevm-slimmed/boot.log\n"
                 "- %s /var/spool/abrt/ccpp-2012-09-28-09:53:26-4080\n"
                 "- %s /var/log/messages\n") % \
                 (cls.plugin_name, cls.plugin_name,
                  cls.plugin_name)

    def get_intro_text(self):
        return _('\nType the number of the symptom to view,\n'
                 'or \'e\' to return to the previous menu.')

    def get_prompt_text(self):
        return _('Select a Symptom: ')

    def get_sub_menu_options(self):
        return self._submenu_opts

    def _check_input(self):
        msg = _("ERROR: %s requires a file.")\
                    % self.plugin_name

        if not self._line:
            if common.is_interactive():
                userinput = []
                try:
                    print _('Please provide the file, or text '
                            'to be analyzed: Ctrl-d on an empty line to '
                            'submit:')
                    while True:
                        userinput.append(raw_input())
                except EOFError:
                    # User pressed Ctrl-d
                    self._line = str('\n'.join(userinput)).decode(
                                                            'utf-8').strip()
            else:
                print msg
                raise Exception(msg)

    def validate_args(self):
        # Check for required arguments.
        self._check_input()

    def postinit(self):
        '''
        This is where the work goes down, call do_analysis to do that work
        '''
        self._submenu_opts = deque()
        self._sections = {}
        Symptoms.AnalyzerPlugin.symptoms = []
        self.do_analysis(self._line)

    def non_interactive_action(self):
        '''
        Running in non-interactive mode, just dump the text to screen
        '''
        for res in self.results:
            line = "At Line: %d \n Symptom: %s" % (res.line_num,
                        (res.before_line + '\n' + res.token_string))
            try:
                print line.encode("UTF-8", 'replace')
            # pylint: disable=W0703
            except Exception, e:
                logger.log(logging.WARNING, e)
                import sys
                print line.encode(sys.getdefaultencoding(), 'replace')

    def interactive_action(self, display_option=None):
        '''
        This gets invoked when running in interactive mode
        Basically just a hook to get your sub command (symptom) invoked
        '''
        if display_option.display_text == self.ALL:
            doc = u''
            for opt in self._submenu_opts:
                if opt.display_text != self.ALL:
                    doc += self._sections[opt]
            pydoc.pipepager(doc.encode("UTF-8", 'replace'),
                            cmd='less -R')
        else:
            lh = LaunchHelper(Symptom)
            lh.run(None, display_option)

    def do_analysis(self, filename):
        '''
        Call the analyzer helper to do the actual work and build the Display
        '''
        # Call analyze, this will do the work
        self.results = analyzer.Analyzer.analyze(filename)

        for res in self.results:
            # This builds the input for the Interactive display
            # DisplayOptions get appended to the _submenu_opts
            # Displays as "index [lineNumber] begin description\n"
            #                                  "2nd part of desc"
            disp_opt = ObjectDisplayOption('[' + str(res.line_num) +
                                     ']  '
                                     + (res.before_line +
                                        '\n\t\t' +
                                        res.source_line),
                                     'interactive_action', {'symptom': res})
            self._submenu_opts.append(disp_opt)
            self._sections[disp_opt] = (res.before_line + res.token_string)
