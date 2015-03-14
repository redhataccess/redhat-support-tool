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
from redhat_support_tool.plugins import InteractivePlugin, ObjectDisplayOption
from redhat_support_tool.helpers.constants import Constants
from redhat_support_tool.helpers import common
from redhat_support_tool.helpers.launchhelper import LaunchHelper
from redhat_support_tool.plugins.get_attachment import GetAttachment
import pydoc
import redhat_support_tool.helpers.apihelper as apihelper
import logging

__author__ = 'Spenser Shumaker <sshumake@redhat.com>'

logger = logging.getLogger("redhat_support_tool.plugins.list_attachment")


class ListAttachments(InteractivePlugin):
    plugin_name = 'listattachments'
    ALL = _("Display all attachments")
    _submenu_opts = None
    _sections = None
    case = None
    aAry = None

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
        return _('Use the \'%s\' command to list attachments for the specified'
         ' support case.') % cls.plugin_name

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
         '- %s 12345678') % (cls.plugin_name)

    def get_intro_text(self):
        return _('\nType the number of the attachment to download or \'e\' '
                 'to return to the previous menu.')

    def get_prompt_text(self):
        return _('Select an attachment: ')

    def get_sub_menu_options(self):
        return self._submenu_opts

    def _check_case_number(self):
        msg = _("ERROR: %s requires a case.")\
                    % self.plugin_name
        self.case = None

        if self._args:
            self.case = self._args[0]
        elif common.is_interactive():
            line = raw_input(_('Please provide the case number(or \'q\' '
                                       'to exit): '))
            line = str(line).strip()
            if line == 'q':
                raise Exception()
            self.case = line
        else:
            print msg
            raise Exception(msg)

    def validate_args(self):
        # Check for required arguments.
        self._check_case_number()

    def postinit(self):
        self._submenu_opts = deque()
        self._sections = {}
        api = None
        try:
            api = apihelper.get_api()
            self.aAry = api.attachments.list(self.case)
            if not self._parse_cases():
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
            msg = _("Unable to list attachments")
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
        # Used by GetCase
        else:
            uuid = None
            uuid = display_option.stored_obj
            lh = LaunchHelper(GetAttachment)
            lh.run('-c %s -u %s' % (self.case, uuid))

    def _parse_cases(self):
        '''
        Use this for non-interactive display of results.
        '''
        try:
            for val in self.aAry:
                doc = u''
                doc += '%-14s  %-60s\n' % (Constants.ATTACH_CREATE,
                                           common.iso8601tolocal(
                                                    val.get_createdDate()))
                doc += '%-14s  %-60s\n' % (Constants.ATTACH_CREATE_BY,
                                           val.get_createdBy())
                doc += '%-14s  %-60s\n' % (Constants.ATTACH_FILE_NAME,
                                           val.get_fileName())
                doc += '%-14s  %-60s\n' % (Constants.ATTACH_DESCRIPTION,
                                           val.get_description())
                doc += '%-14s  %-60s\n' % (Constants.ATTACH_LENGTH,
                                           common.get_friendly_file_length(
                                                    val.get_length()))
                doc += '%-14s  %-60s\n' % (Constants.UUID,
                                           val.get_uuid())
                doc += '%-14s  %-60s' % (Constants.URL,
                                         val.get_uri())
                doc += '\n\n%s%s%s\n\n' % (Constants.BOLD,
                                           str('-' * Constants.MAX_RULE),
                                           Constants.END)
                disp_opt_text = "%-24s  %-40s  %-50s" % (val.get_fileName(),
                                                         val.get_uuid(),
                                                         val.get_description())
                disp_opt = ObjectDisplayOption(disp_opt_text,
                                               'interactive_action',
                                               val.get_uuid())
                self._submenu_opts.append(disp_opt)
                self._sections[disp_opt] = doc
        # pylint: disable=W0702
        except:
            msg = _('ERROR: problem parsing the attachments.')
            print msg
            logger.log(logging.WARNING, msg)
            return False
        return True
