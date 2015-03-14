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
from redhat_support_tool.helpers.confighelper import _
from redhat_support_tool.helpers.confighelper import EmptyValueError
from redhat_support_tool.plugins import InteractivePlugin, DisplayOption
from redhat_support_tool.helpers.constants import Constants
import pydoc
import redhat_support_tool.helpers.apihelper as apihelper
import logging

__author__ = 'Spenser Shumaker <sshumake@redhat.com>'
logger = logging.getLogger("redhat_support_tool.plugins.list_entitlements")


class ListEntitlements(InteractivePlugin):
    plugin_name = 'listentitlements'
    ALL = _("Display all entitlements")
    _submenu_opts = None
    _sections = None
    _entitlementsAry = None

    @classmethod
    def get_usage(cls):
        '''
        The usage statement that will be printed by OptionParser.

        Example:
            - %prog -c CASENUMBER [options] <comment text here>
        Important: %prog is a OptionParser built-in.  Use it!
        '''
        return _('%prog')

    @classmethod
    def get_desc(cls):
        '''
        The description statement that will be printed by OptionParser.

        Example:
            - 'Use the \'%s\' command to add a comment to a case.'\
             % cls.plugin_name
        '''
        return _('Use the \'%s\' command to list your current entitlements.')\
             % cls.plugin_name

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
                 '  - %s') % (cls.plugin_name)

    def get_intro_text(self):
        return _('\nType the number of the entitlement to view or \'e\' '
                 'to return to the previous menu.')

    def get_prompt_text(self):
        return _('Select an entitlement: ')

    def get_sub_menu_options(self):
        return self._submenu_opts

    def postinit(self):
        self._submenu_opts = deque()
        self._sections = {}
        api = None
        try:
            api = apihelper.get_api()
            self._entitlementsAry = api.entitlements.list()
            if not self._parse_entitlements():
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
            msg = _("Unable to list entitlements")
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
        # pylint: disable=W0703
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

    def _parse_entitlements(self):
        '''
        Use this for non-interactive display of results.
        '''
        try:
            for val in self._entitlementsAry:
                doc = u''
                doc += '%-15s  %s\n' % (Constants.ENTITLEMENT_NAME,
                                           val.get_name())
                doc += '%-15s  %s\n' % (Constants.ENTITLEMENT_SERVICE_LEVEL,
                                           val.get_serviceLevel())
                doc += '%-15s  %s\n' % (Constants.ENTITLEMENT_SLA,
                                           val.get_sla())
                doc += '%-15s  %s\n' % (Constants.ENTITLEMENT_SUPPORT_LEVEL,
                                           val.get_supportLevel())
                doc += '%-15s  %s\n' % (Constants.ENTITLEMENT_START_DATE,
                                           val.get_startDate())
                doc += '%-15s  %s\n' % (Constants.ENTITLEMENT_END_DATE,
                                           val.get_endDate())
                doc += '\n%s%s%s\n\n' % (Constants.BOLD,
                                           str('-' * Constants.MAX_RULE),
                                           Constants.END)
                disp_opt = DisplayOption(val.get_name(),
                                         'interactive_action')
                self._submenu_opts.append(disp_opt)
                self._sections[disp_opt] = doc
        # pylint: disable=W0702
        except:
            msg = _('ERROR: problem parsing the cases.')
            print msg
            logger.log(logging.WARNING, msg)
            return False
        if(disp_opt):
            return True
        return False
