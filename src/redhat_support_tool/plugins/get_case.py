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
from redhat_support_tool.plugins import InteractivePlugin, DisplayOption, \
                                        ObjectDisplayOption
from redhat_support_tool.helpers import common
from redhat_support_tool.helpers.launchhelper import LaunchHelper
from redhat_support_tool.helpers.genericinteractiveprompt import GenericPrompt
from redhat_support_tool.plugins.list_attachments import ListAttachments
from redhat_support_tool.plugins.add_attachment import AddAttachment
from redhat_support_tool.plugins.add_comment import AddComment
from redhat_support_tool.plugins.kb import Kb
from redhat_support_tool.plugins.modify_case import ModifyCase
from redhat_support_tool.helpers.constants import Constants
import redhat_support_tool.helpers.recommendationprompter as \
                                        recommendationprompter
import pydoc
import redhat_support_tool.helpers.apihelper as apihelper
import logging
import textwrap

__author__ = 'Keith Robertson <kroberts@redhat.com>'
__author__ = 'Spenser Shumaker <sshumake@redhat.com>'
logger = logging.getLogger("redhat_support_tool.plugins.case")


class GetCase(InteractivePlugin):
    plugin_name = 'getcase'
    ALL = _("Display all cases")
    _submenu_opts = None
    _sections = None
    case = None
    case_obj = None

    @classmethod
    def get_usage(cls):
        '''
        The usage statement that will be printed by OptionParser.

        Example:
            - %prog -c CASENUMBER [options] <comment text here>
        Important: %prog is an OptionParser built-in.  Use it!
        '''
        return _('%prog CASENUMBER')

    @classmethod
    def get_desc(cls):
        '''
        The description statement that will be printed by OptionParser.

        Example:
            - 'Use the \'%s\' command to add a comment to a case.'\
             % cls.plugin_name
        '''
        return _('Use the \'%s\' command to find a specific case by \
number.') % cls.plugin_name

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
                 '  - %s <case number here>') % (cls.plugin_name)

    def get_intro_text(self):
        return _('\nType the number of the section to view or \'e\' '
                 'to return to the previous menu.')

    def get_prompt_text(self):
        return _('Option: ')

    def get_sub_menu_options(self):
        return self._submenu_opts

    def _check_case_number(self):
        msg = _("ERROR: %s requires a case number.")\
                    % self.plugin_name
        self.case = ''
        if self._args:
            self.case = ' '.join(self._args)
        elif common.is_interactive():
            line = raw_input(_('Please provide a case number (or \'q\' '
                                       'to exit): '))
            line = str(line).strip()
            if line == 'q':
                raise Exception()
            if str(line).strip():
                self.case = line
            else:
                    print msg
                    raise Exception(msg)
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
            self.case_obj = api.cases.get(self.case)
            # add the case group info (if it exists) to the case object
            self.case_obj.group = None
            case_group = self.case_obj.get_folderNumber()
            if case_group:
                self.case_obj.group = api.groups.get(case_group)
            if not self._parse_sections(self.case_obj):
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
            msg = _("Unable to find case")
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
            if display_option.display_text == Constants.CASE_GET_ATTACH:
                lh = LaunchHelper(ListAttachments)
                lh.run('%s' % self.case)
            elif display_option.display_text == Constants.CASE_ADD_ATTACH:
                lh = LaunchHelper(AddAttachment)
                lh.run('-c %s' % self.case)
            elif display_option.display_text == Constants.CASE_ADD_COMMENT:
                lh = LaunchHelper(AddComment)
                lh.run('-c %s' % self.case)
                # Check if we need to reload the case as adding comments may
                # result in new options for case view.
                comments = self.case_obj.get_comments()
                if comments is None or len(comments) == 0:
                    self.postinit()
                    self.opts_updated = True
            elif (display_option.display_text == Constants.CASE_RECOMMENDATIONS
                  and common.is_interactive()):
                lh = LaunchHelper(GenericPrompt)
                lh.run('', display_option)
            elif (display_option.display_text == Constants.CASE_MODIFY
                  and common.is_interactive()):
                lh = LaunchHelper(ModifyCase)
                lh.run('%s' % self.case)
            else:
                doc = self._sections[display_option]
                pydoc.pipepager(doc.encode("UTF-8", 'replace'), cmd='less -R')

    def _parse_sections(self, case):
        '''
        Find available sections, format, and put in dictionary.
        '''
        try:
            # Info (all cases should have this):
            doc = u''
            doc += '\n%s%s%s\n' % (Constants.BOLD,
                                   Constants.CASE_DETAILS,
                                   Constants.END)
            doc += '%s%s%s\n' % (Constants.BOLD,
                                 str(self.ruler * Constants.MAX_RULE),
                                 Constants.END)
            doc += '%-20s  %-40s\n' % (Constants.CASE_NUMBER,
                                       case.get_caseNumber())
            doc += '%-20s  %-40s\n' % (Constants.CASE_TYPE,
                                       case.get_type())
            doc += '%-20s  %-40s\n' % (Constants.CASE_SEVERITY,
                                       case.get_severity())
            doc += '%-20s  %-40s\n' % (Constants.CASE_STATUS,
                                       case.get_status())
            doc += '%-20s  %-40s\n\n' % (Constants.CASE_AID,
                                         case.get_alternateId())
            doc += '%-20s  %-40s\n' % (Constants.CASE_PROD,
                                       case.get_product())
            doc += '%-20s  %-40s\n' % (Constants.CASE_VER,
                                       case.get_version())

            if case.get_entitlement() is None:
                doc += '%-20s  %-40s\n' % (Constants.CASE_SLA, ' ')
            else:
                doc += '%-20s  %-40s\n' % (Constants.CASE_SLA,
                                        case.get_entitlement().get_sla())
            doc += '%-20s  %-40s\n' % (Constants.CASE_OWNER,
                                       case.get_contactName())
            doc += '%-20s  %-40s\n\n' % (Constants.CASE_RHOWN,
                                         case.get_owner())
            if case.group:
                doc += '%-20s  %-40s\n' % (Constants.CASE_GRP,
                                           case.group.get_name())
            else:
                doc += '%-20s  %-40s\n' % (Constants.CASE_GRP, 'None')
            doc += '%-20s  %-40s\n' % (Constants.CASE_OPENED,
                            common.iso8601tolocal(case.get_createdDate()))
            doc += '%-20s  %-40s\n' % (Constants.CASE_OPENEDBY,
                                       case.get_createdBy())
            doc += '%-20s  %-40s\n' % (Constants.CASE_UPDATED,
                        common.iso8601tolocal(case.get_lastModifiedDate()))
            doc += '%-20s  %-40s\n\n' % (Constants.CASE_UPDATEDBY,
                            case.get_lastModifiedBy())
            doc += '%-20s  %-40s\n\n' % (Constants.CASE_SUMMARY,
                                         case.get_summary())
            disp_opt = DisplayOption(Constants.CASE_DETAILS,
                                         'interactive_action')
            self._submenu_opts.append(disp_opt)
            self._sections[disp_opt] = doc

            if common.is_interactive():
                disp_opt = DisplayOption(Constants.CASE_MODIFY,
                                         'interactive_action')
                self._submenu_opts.append(disp_opt)

            # Description
            des = case.get_description()
            if des is not None:
                doc = u''
                doc += '\n%s%s%s\n' % (Constants.BOLD,
                                       Constants.CASE_DESCRIPTION,
                                       Constants.END)
                doc += '%s%s%s\n' % (Constants.BOLD,
                                     str(self.ruler * Constants.MAX_RULE),
                                     Constants.END)
                doc += '%s\n' % des
                disp_opt = DisplayOption(Constants.CASE_DESCRIPTION,
                                         'interactive_action')
                self._submenu_opts.append(disp_opt)
                self._sections[disp_opt] = doc

            # Comments
            commentAry = case.get_comments()
            num_comments = len(commentAry)
            if commentAry is not None and num_comments > 0:
                doc = u''
                doc += '\n%s%s%s\n' % (Constants.BOLD,
                                       Constants.CASE_DISCUSSION,
                                       Constants.END)
                doc += '%s%s%s\n' % (Constants.BOLD,
                                     str(self.ruler * Constants.MAX_RULE),
                                     Constants.END)
                for i, cmt in enumerate(commentAry):
                    cmt_type = 'private'
                    if cmt.get_public():
                        cmt_type = 'public'
                    doc += '%-20s  #%s %s(%s)%s\n' % \
                           (Constants.COMMENT, num_comments-i,
                            Constants.BOLD if cmt_type == 'private' else
                            Constants.END, cmt_type, Constants.END)
                    doc += '%-20s  %-40s\n' % (Constants.CASE_CMT_AUTHOR,
                                               cmt.get_lastModifiedBy())
                    doc += '%-20s  %-40s\n\n' % (Constants.CASE_CMT_DATE,
                            common.iso8601tolocal(cmt.get_lastModifiedDate()))
                    doc += cmt.get_text()
                    doc += '\n\n%s%s%s\n\n' % (Constants.BOLD,
                                               str('-' * Constants.MAX_RULE),
                                               Constants.END)
                disp_opt = DisplayOption(Constants.CASE_DISCUSSION,
                                         'interactive_action')
                self._submenu_opts.append(disp_opt)
                self._sections[disp_opt] = doc

            recommendAry = case.get_recommendations()
            if recommendAry is not None and len(recommendAry) > 0:
                doc = u''
                doc += '\n%s%s%s\n' % (Constants.BOLD,
                                       Constants.CASE_RECOMMENDATIONS,
                                       Constants.END)
                doc += '%s%s%s\n' % (Constants.BOLD,
                                     str(self.ruler * Constants.MAX_RULE),
                                     Constants.END)

                # For de-duplication this is now in a helper module,
                # generate_metadata will return the formatted doc for non-
                # interactive prompts, plus the prompt for interactive users.
                disp_opt, recdoc = recommendationprompter.generate_metadata(
                                                                recommendAry)
                doc += recdoc

                self._submenu_opts.append(disp_opt)
                self._sections[disp_opt] = doc

            # Get Attachments

            disp_opt = DisplayOption(Constants.CASE_GET_ATTACH,
                                         'interactive_action')
            self._submenu_opts.append(disp_opt)
            self._sections[disp_opt] = Constants.CASE_GET_ATTACH

            # Add Attachment
            disp_opt = DisplayOption(Constants.CASE_ADD_ATTACH,
                                         'interactive_action')
            self._submenu_opts.append(disp_opt)
            self._sections[disp_opt] = Constants.CASE_ADD_ATTACH

            # Comment
            disp_opt = DisplayOption(Constants.CASE_ADD_COMMENT,
                                         'interactive_action')
            self._submenu_opts.append(disp_opt)
            self._sections[disp_opt] = Constants.CASE_ADD_COMMENT
        except Exception:
            msg = _('ERROR: problem parsing the cases.')
            print msg
            logger.log(logging.WARNING, msg)
            return False
        return True
