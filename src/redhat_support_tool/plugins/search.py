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
from optparse import Option
from collections import deque
from redhat_support_lib.infrastructure.errors import RequestError, \
    ConnectionError
from redhat_support_tool.helpers.confighelper import _
from redhat_support_tool.helpers.confighelper import EmptyValueError
from redhat_support_tool.plugins import InteractivePlugin, ObjectDisplayOption
from redhat_support_tool.helpers.constants import Constants
from redhat_support_tool.helpers import common
from redhat_support_tool.helpers import confighelper
from redhat_support_tool.helpers.launchhelper import LaunchHelper
from redhat_support_tool.plugins.kb import Kb
import redhat_support_tool.helpers.apihelper as apihelper
import logging
import re


__author__ = 'Keith Robertson <kroberts@redhat.com>'
__author__ = 'Spenser Shumaker <sshumake@redhat.com>'
logger = logging.getLogger("redhat_support_tool.plugins.search")


class Search(InteractivePlugin):
    plugin_name = 'search'

    partial_entries = _('%s of %s solutions displayed. Type \'m\' to'
                        ' see more, \'r\' to start from the beginning'
                        ' again, or \'?\' for help with the codes displayed'
                        ' in the above output.')
    end_of_entries = _('No more solutions to display')
    more_entries_maybe = _('More solutions may be available. Type \'m\' to try'
                           ' and find more')

    state_explanations = {'WIP': _('Work In Progress: This solution is a Work'
                                   ' in Progress.'),
                          'UNV': _('Unverified: This solution has not yet been'
                                   ' verified to work by Red Hat customers.'),
                          'VER': _('Verified: This solution has been verified'
                                   ' to work by Red Hat Customers and Support'
                                   ' Engineers for the specified product'
                                   ' version(s).')}

    # Help should not print the option list
    help_is_options = False

    _submenu_opts = None
    _sections = None
    _solAry = None

    # Record the last offset value used with the API, and the maximum results
    # we should display for one search query.
    _nextOffset = 0
    _MAX_OFFSET = confighelper.get_config_helper().get(option='max_results')
    _MAX_OFFSET = 500 if not _MAX_OFFSET else int(_MAX_OFFSET)
    _limit = 50 if _MAX_OFFSET >= 50 else _MAX_OFFSET

    @classmethod
    def get_usage(cls):
        '''
        The usage statement that will be printed by OptionParser.

        Example:
            - %prog -c CASENUMBER [options] <comment text here>
        Important: %prog is a OptionParser built-in.  Use it!
        '''
        return _('%prog [options] <keywords>')

    @classmethod
    def get_desc(cls):
        '''
        The description statement that will be printed by OptionParser.

        Example:
            - 'Use the \'%s\' command to add a comment to a case.'\
             % cls.plugin_name
        '''
        return _('Use the \'%s\' command to search the entire knowledge base '
                 'for solutions with given keywords, a log message, program '
                 'configuration variables, etc.') % cls.plugin_name

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
        return _("""Examples:
  - %s RHEV
  - %s -s Starting osa-dispatcher: RHN 9899 Traceback caught""") \
  % (cls.plugin_name, cls.plugin_name)

    @classmethod
    def get_options(cls):
        return [Option("-s", "--summary", dest="summary", default=False,
                        help=_('Display summary information about matched '
                        'articles'), action='store_true')]

    def validate_args(self):
        msg = _("ERROR: %s requires text to search.")\
                    % self.plugin_name

        if not self._line:
            if common.is_interactive():
                line = raw_input(_('Please provide the text to search (or'
                                   ' \'q\' to exit): '))
                line = str(line).strip()
                if line == 'q':
                    raise Exception()
                if str(line).strip():
                    self._line = line
            else:
                print msg
                raise Exception(msg)

    def get_intro_text(self):
        return _('\nType the number of the solution to view or \'e\' '
                 'to return to the previous menu.')

    def get_prompt_text(self):
        return _('Select a Solution: ')

    def get_sub_menu_options(self):
        return self._submenu_opts

    def get_more_options(self, num_options):
        if (len(self._solAry) < self._nextOffset or
            len(self._solAry) == 0 or
            self._nextOffset >= self._MAX_OFFSET):
            # Either we did not max out on results last time, there were
            # no results last time, or we have seen more than _MAX_OFFSET
            # results.
            return False

        # Strata introduces an issue where if the limit > 50, it will only
        # return 50 results. This creates a potential issue if the terminal
        # size is greater than 53.
        limit = self._get_limit()
        if num_options > limit:
            num_options = limit

        searchopts = {'limit': num_options, 'offset': self._nextOffset}
        self._nextOffset += num_options
        newresults = self._get_solutions(searchopts)

        if len(newresults) == 0:
            return False

        self._solAry.extend(newresults)
        self._parse_solutions(newresults)
        return True

    def do_help(self, line):
        doclines = [_('Red Hat Support assigns a state with all knowledge'
                      ' solutions, which is displayed in the above output.'),
                    '',
                    _('The current states are:')]

        for doc in doclines:
            print doc

        for state in self.state_explanations.keys():
            print '  %s - %s' % (state, self.state_explanations[state])

        common.do_help(self)

    def postinit(self):
        self._submenu_opts = deque()
        self._sections = {}

        searchopts = {'limit': self._limit, 'offset': 0}
        self._nextOffset = self._limit
        self._solAry = self._get_solutions(searchopts)

        if not self._parse_solutions(self._solAry):
            msg = _("Unable to find solutions")
            print msg
            logger.log(logging.WARNING, msg)
            raise Exception()

        if not common.is_interactive():
            while self.get_more_options(self._limit):
                continue

    def non_interactive_action(self):
        doc = u''
        for opt in self._submenu_opts:
            doc += self._sections[opt]
        try:
            print doc.encode("UTF-8", 'replace')
        # pylint: disable=W0703
        except Exception, e:
            # There are some truly bizarre errors when you pipe
            # the output from python's 'print' function with sys encoding
            # set to ascii. These errors seem to manifes when you pipe
            # to something like 'more' or 'less'.  You'll get encoding
            # errors. Curiously, you don't see them with 'grep' or even
            # simply piping to terminal.  WTF :(
            logger.log(logging.WARNING, e)
            import sys
            print doc.encode(sys.getdefaultencoding(), 'replace')

    def interactive_action(self, display_option=None):
        solution_id = None
        try:
            solution_id = display_option.stored_obj
            lh = LaunchHelper(Kb)
            lh.run(solution_id)
        except:
            raise Exception()

    def _get_solutions(self, searchopts):
        api = None
        try:
            api = apihelper.get_api()
            return api.solutions.list(self._line, searchopts=searchopts)
        except EmptyValueError, eve:
            msg = _('ERROR: %s') % str(eve)
            print msg
            logger.log(logging.WARNING, msg)
            raise
        except RequestError, re:
            msg = _('Unable to connect to support services API. '
                    'Reason: %s') % re.reason
            print msg
            logger.log(logging.WARNING, msg)
            raise
        except ConnectionError:
            msg = _('Problem connecting to the support services '
                    'API.  Is the service accessible from this host?')
            print msg
            logger.log(logging.WARNING, msg)
            raise
        except Exception:
            msg = _("Unable to find solutions")
            print msg
            logger.log(logging.WARNING, msg)
            raise

    def _parse_solutions(self, solAry):
        '''
        Use this for non-interactive display of results.
        '''
        try:
            for val in solAry:
                # doc is displayed in non-interactive mode
                doc = u''
                doc += '%-8s %-60s\n' % ('%s:' % Constants.TITLE,
                                           val.get_title())
                if self._options['summary']: 
                    summary = val.get_abstract()
                    if summary:
                        summary = " ".join(summary.replace('\n', ' ').split())
                    doc += '%-8s %-60s\n' % (Constants.CASE_SUMMARY, summary)
                doc += '%-8s %-60s\n' % (Constants.ID,
                                           val.get_id())
                kcsState = val.get_kcsState()[0:3].upper()
                kcsStateExplanation = self.state_explanations.get(kcsState, '')
                doc += _('State:   %s\n' % (kcsStateExplanation))
                vuri = val.get_view_uri()
                if(vuri):
                    doc += '%-8s %-60s' % (Constants.URL, vuri)
                else:
                    doc += '%-8s %-60s' % (Constants.URL,
                                           re.sub("api\.|/rs", "",
                                                  val.get_uri()))
                doc += '\n\n%s%s%s\n\n' % (Constants.BOLD,
                                           str('-' * Constants.MAX_RULE),
                                           Constants.END)

                # disp_opt_text is displayed in interactive mode
                if confighelper.get_config_helper().get(option='ponies'):
                    published_state = val.get_ModerationState()[0].upper()
                    disp_opt_text = '[%7s:%s:%s] %s' % (val.get_id(),
                                                     kcsState,
                                                     published_state,
                                                     val.get_title())
                else:
                    disp_opt_text = '[%7s:%s] %s' % (val.get_id(),
                                                     kcsState,
                                                     val.get_title())
                # TODO: nicely display the summary within disp_opt_text
                if self._options['summary']:
                    disp_opt_text += ' *** %s %s' % (Constants.CASE_SUMMARY,
                                                     summary)
                disp_opt = ObjectDisplayOption(disp_opt_text,
                                               'interactive_action',
                                               val.get_id())
                self._submenu_opts.append(disp_opt)
                self._sections[disp_opt] = doc
        # pylint: disable=W0702
        except:
            msg = _('ERROR: problem parsing the solutions.')
            print msg
            logger.log(logging.WARNING, msg)
            return False
        if(disp_opt):
            return True
        return False

    def _get_limit(self):
        limit = self._limit
        remaining = self._MAX_OFFSET - self._nextOffset
        return limit if (remaining) >= limit else (remaining) % limit