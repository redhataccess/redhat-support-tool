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
from redhat_support_lib.infrastructure.errors import RequestError, \
    ConnectionError
from redhat_support_tool.helpers.confighelper import EmptyValueError, _
from redhat_support_tool.plugins import InteractivePlugin, DisplayOption
from redhat_support_tool.helpers.constants import Constants
from redhat_support_tool.helpers import common
import os
import pydoc
import redhat_support_tool.helpers.apihelper as apihelper
import logging

__author__ = 'Keith Robertson <kroberts@redhat.com>'
logger = logging.getLogger("redhat_support_tool.plugins.kb")


class Kb(InteractivePlugin):
    plugin_name = 'kb'
    ALL = _("Display all sections")
    _submenu_opts = None
    _sections = None
    solutionID = None

    @classmethod
    def get_usage(cls):
        '''
        The usage statement that will be printed by OptionParser.

        Example:
            - %prog -c CASENUMBER [options] <comment text here>
        Important: %prog is a OptionParser built-in.  Use it!
        '''
        return _('%prog <knowledge base solution ID>')

    @classmethod
    def get_desc(cls):
        '''
        The description statement that will be printed by OptionParser.

        Example:
            - 'Use the \'%s\' command to add a comment to a case.'\
             % cls.plugin_name
        '''
        return _('Use the \'%s\' command to find a knowledge base solution '
                'by ID') % cls.plugin_name

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
        return _('Example:\n'
                 '  - %s 63568') % (cls.plugin_name)

    def get_intro_text(self):
        return _('\nType the number of the section to view or \'e\' '
                 'to return to the previous menu.')

    def get_prompt_text(self):
        return _('Section: ')

    def get_sub_menu_options(self):
        return self._submenu_opts

    def _check_solution_id(self):
        msg = _("ERROR: %s requires a knowledge base solution ID. "
                    "Try \'help %s\' for more information.") % \
                        (self.plugin_name,
                         self.plugin_name)
        self.solutionID = None

        if self._args:
            self.solutionID = self._args[0]
        elif common.is_interactive():
            line = raw_input(_('Please provide the knowledge base '
                               'solution ID (or \'q\' to exit): '))
            if line == 'q':
                raise Exception()
            line = str(line).strip()
            if str(line).strip():
                self.solutionID = line
        else:
            print msg
            raise Exception(msg)

    def validate_args(self):
        # Check for required arguments.
        self._check_solution_id()

    def postinit(self):
        kb_object = None
        self._submenu_opts = deque()
        self._sections = {}
        api = None
        try:
            api = apihelper.get_api()
            kb_object = api.solutions.get(self.solutionID)
            if not self._parse_solution_sections(kb_object):
                raise Exception()
        except Exception:
            # See if the given ID is an article.
            try:
                kb_object = api.articles.get(self.solutionID)
                if not self._parse_article_sections(kb_object):
                    raise Exception()
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
                msg = _("Unable to find a KB with an ID of %s")\
                         % self.solutionID
                print msg
                logger.log(logging.WARNING, msg)
                raise

    def non_interactive_action(self):
        doc = u''
        for opt in self._submenu_opts:
            if opt.display_text != self.ALL:
                doc += self._sections[opt]
        try:
            print doc.encode("UTF-8", 'replace')
        except Exception, e:
            # There are some truly bizarre errors when you pipe
            # the output from python's 'print' function with sys encoding
            # set to ascii. These errors seem to manifes when you pipe
            # to something like 'more' or 'less'.  You'll get encoding errors.
            # Curiously, you don't see them with 'grep' or even simply piping
            # to terminal.  WTF :(
            logger.log(logging.WARNING, e)
            import sys
            print doc.encode(sys.getdefaultencoding(),
                             'replace')

    def interactive_action(self, display_option=None):
        if display_option.display_text == self.ALL:
            doc = u''
            for opt in self._submenu_opts:
                if opt.display_text != self.ALL:
                    doc += self._sections[opt]
            pydoc.pipepager(doc.encode("UTF-8", 'replace'),
                            cmd='less -R')
        else:
            doc = self._sections[display_option]
            pydoc.pipepager(doc.encode("UTF-8", 'replace'), cmd='less -R')

    def _parse_solution_sections(self, sol):
        if not sol:
            return False
        try:
            # Get Title:
            doc = u''
            doc += '\n%s%s%s\n' % (Constants.BOLD,
                                   Constants.TITLE,
                                   Constants.END)
            doc += '%s%s%s\n' % (Constants.BOLD,
                                 str(self.ruler * Constants.MAX_RULE),
                                 Constants.END)
            doc += '%s\n' % sol.get_title()
            doc += '%-10s  %s\n' % (Constants.URL, sol.get_view_uri())
            doc = doc.replace('\r\n', os.linesep)  # Set linesep to platform.
            disp_opt = DisplayOption(Constants.TITLE,
                                     'interactive_action')
            self._submenu_opts.append(disp_opt)
            self._sections[disp_opt] = doc

            # Get Issue
            issue = sol.get_issue()
            if issue is not None and issue.get_text() is not None:
                doc = u''
                doc += '\n%s%s%s\n' % (Constants.BOLD,
                                       Constants.ISSUE,
                                       Constants.END)
                doc += '%s%s%s\n' % (Constants.BOLD,
                                     str(self.ruler * Constants.MAX_RULE),
                                     Constants.END)
                doc += '%s\n' % issue.get_text()
                disp_opt = DisplayOption(Constants.ISSUE,
                                         'interactive_action')
                self._submenu_opts.append(disp_opt)
                self._sections[disp_opt] = doc

            # Print Environment
            env = sol.get_environment()
            if env is not None and env.get_text() is not None:
                doc = u''
                doc += '\n%s%s%s\n' % (Constants.BOLD,
                                       Constants.ENV,
                                       Constants.END)
                doc += '%s%s%s\n' % (Constants.BOLD,
                                     str(self.ruler * Constants.MAX_RULE),
                                     Constants.END)
                doc += '%s\n' % env.get_text()
                disp_opt = DisplayOption(Constants.ENV,
                                         'interactive_action')
                self._submenu_opts.append(disp_opt)
                self._sections[disp_opt] = doc

            # Print Resolution
            res = sol.get_resolution()
            if res is not None and res.get_text() is not None:
                doc = u''
                doc += '\n%s%s%s\n' % (Constants.BOLD,
                                       Constants.RESOLUTION,
                                       Constants.END)
                doc += '%s%s%s\n' % (Constants.BOLD,
                                     str(self.ruler * Constants.MAX_RULE),
                                     Constants.END)
                doc += '%s\n' % res.get_text()
                disp_opt = DisplayOption(Constants.RESOLUTION,
                                         'interactive_action')
                self._submenu_opts.append(disp_opt)
                self._sections[disp_opt] = doc

            # Print Root Cause
            rc = sol.get_rootCause()
            if rc is not None and rc.get_text() is not None:
                doc = u''
                doc += '\n%s%s%s\n' % (Constants.BOLD,
                                       Constants.ROOT_CAUSE,
                                       Constants.END)
                doc += '%s%s%s\n' % (Constants.BOLD,
                                     str(self.ruler * Constants.MAX_RULE),
                                     Constants.END)
                doc += '%s\n' % rc.get_text()
                disp_opt = DisplayOption(Constants.ROOT_CAUSE,
                                         'interactive_action')
                self._submenu_opts.append(disp_opt)
                self._sections[disp_opt] = doc

            # Print Diagnostic Steps
            diag = sol.get_internalDiagnosticSteps()
            if diag is not None and diag.get_text() is not None:
                doc = u''
                doc += '\n%s%s%s\n' % (Constants.BOLD,
                                       Constants.DIAG,
                                       Constants.END)
                doc += '%s%s%s\n' % (Constants.BOLD,
                                     str(self.ruler * Constants.MAX_RULE),
                                     Constants.END)
                doc += '%s\n' % diag.get_text()
                disp_opt = DisplayOption(Constants.DIAG,
                                         'interactive_action')
                self._submenu_opts.append(disp_opt)
                self._sections[disp_opt] = doc

            # Print all sections
            disp_opt = DisplayOption(self.ALL,
                                     'interactive_action')
            self._submenu_opts.append(disp_opt)
            self._sections[disp_opt] = None
        except:
            msg = _('ERROR: problem parsing the solution.')
            print msg
            logger.log(logging.WARNING, msg)
            return False
        return True

    def _parse_article_sections(self, art):
        if not art:
            return False
        try:
            # Get Title:
            doc = u''
            doc += '\n%s%s%s\n' % (Constants.BOLD, Constants.TITLE,
                                   Constants.END)
            doc += '%s%s%s\n' % (Constants.BOLD,
                                 str(self.ruler * Constants.MAX_RULE),
                                 Constants.END)
            doc += '%s\n' % art.get_title()
            doc += '%-10s  %s\n' % (Constants.URL, art.get_view_uri())
            disp_opt = DisplayOption(Constants.TITLE,
                                     'interactive_action')
            self._submenu_opts.append(disp_opt)
            self._sections[disp_opt] = doc

            # Get Body
            body = art.get_body()
            if body:
                doc = u''
                doc += '\n%s%s%s\n' % (Constants.BOLD,
                                       Constants.ISSUE,
                                       Constants.END)
                doc += '%s%s%s\n' % (Constants.BOLD,
                                     str(self.ruler * Constants.MAX_RULE),
                                     Constants.END)
                doc += '%s\n' % body
                disp_opt = DisplayOption(Constants.ISSUE,
                                         'interactive_action')
                self._submenu_opts.append(disp_opt)
                self._sections[disp_opt] = doc
            # Print all sections
            disp_opt = DisplayOption(self.ALL,
                                     'interactive_action')
            self._submenu_opts.append(disp_opt)
            self._sections[disp_opt] = None
        except:
            msg = _('ERROR: problem parsing the article.')
            print msg
            logger.log(logging.WARNING, msg)
            return False
        return True
