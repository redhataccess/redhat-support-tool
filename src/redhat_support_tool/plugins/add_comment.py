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
from optparse import Option, SUPPRESS_HELP
from redhat_support_lib.infrastructure.errors import RequestError, \
    ConnectionError
from redhat_support_tool.helpers.confighelper import EmptyValueError
from redhat_support_tool.helpers.confighelper import _
from redhat_support_tool.plugins import Plugin
import redhat_support_tool.helpers.apihelper as apihelper
import redhat_support_tool.helpers.common as common
import redhat_support_tool.helpers.confighelper as confighelper
import logging


__author__ = 'Keith Robertson <kroberts@redhat.com>'
__author__ = 'Spenser Shumaker <sshumake@redhat.com>'
logger = logging.getLogger("redhat_support_tool.plugins.add_comment")


class AddComment(Plugin):
    plugin_name = 'addcomment'
    comment = None

    @classmethod
    def get_usage(cls):
        '''
        The usage statement that will be printed by OptionParser.

        Example:
            - %prog -c CASENUMBER [options] <comment text here>
        Important: %prog is a OptionParser built-in.  Use it!
        '''
        return _('%prog -c CASENUMBER <comment text here>')

    @classmethod
    def get_desc(cls):
        '''
        The description statement that will be printed by OptionParser.

        Example:
            - 'Use the \'%s\' command to add a comment to a case.'\
             % cls.plugin_name
        '''
        return _('Use the \'%s\' command to add a comment to a case.')\
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
        return _("""Examples:
- %s -c 12345678""") % cls.plugin_name

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

        def public_opt_callback(option, opt_str, value, parser):
            '''
            Callback function for the public option that converts the string
            into an equivalent boolean value
            '''
            ret = common.str_to_bool(value)
            if ret is None:
                msg = _("ERROR: Unexpected argument to %s: %s\nValid values"
                        " are true or false (default: %s true)"
                        % (opt_str, value, opt_str))
                print msg
                raise Exception(msg)
            else:
                parser.values.public = ret

        public_opt_help = SUPPRESS_HELP
        if confighelper.get_config_helper().get(option='ponies'):
            public_opt_help = \
            _('True or False.  Use this to toggle a public or private comment'
              ' (default=True).  Example: -p false')

        return [Option("-c", "--casenumber", dest="casenumber",
                        help=_('The case number from which the comment '
                        'should be added. (required)'), default=False),
                Option("-p", "--public", dest="public", help=public_opt_help,
                       type='string', action='callback',
                       callback=public_opt_callback)]

    def insert_obj(self, stored_obj):
        self._args = stored_obj

    def _check_case_number(self):
        msg = _("ERROR: %s requires a case number.")\
                % self.plugin_name

        if not self._options['casenumber']:
            if common.is_interactive():
                line = raw_input(_('Please provide a case number(or \'q\' '
                                       'to exit): '))
                line = str(line).strip()
                if line == 'q':
                    raise Exception()
                if str(line).strip():
                    self._options['casenumber'] = line
                else:
                    print msg
                    raise Exception(msg)
            else:
                print msg
                raise Exception(msg)

    def _check_comment(self):
        msg = _("ERROR: %s requires a some text for the comment.")\
                % self.plugin_name

        if self._args:
            try:
                self.comment = u' '.join([unicode(i, 'utf8') for i in
                                          self._args])
            except TypeError:
                self.comment = u' '.join(self._args)
        elif common.is_interactive():
            comment = []
            try:
                print _('Type your comment. Ctrl-d '
                        'on an empty line to submit:')
                while True:
                    comment.append(raw_input())
            except EOFError:
                # User pressed Ctrl-d
                self.comment = str('\n'.join(comment)).strip()
                if self.comment == '':
                    print msg
                    raise Exception(msg)
                self.comment = self.comment.decode('utf-8')
        else:
            print msg
            raise Exception(msg)

    def _check_is_public(self):
        if common.is_interactive() and \
           confighelper.get_config_helper().get(option='ponies'):
            if self._options['public'] is None:
                line = raw_input(_('Is this a public comment ([y]/n)? '))
                if str(line).strip().lower() == 'n':
                    self._options['public'] = False
                else:
                    self._options['public'] = True
        else:
            if self._options['public'] is None:
                self._options['public'] = True

    def validate_args(self):
        self._check_case_number()
        self._check_comment()
        self._check_is_public()

    def non_interactive_action(self):
        api = None
        try:
            api = apihelper.get_api()
            if not self.comment:
                print _('ERROR: The comment has no content.')
                raise Exception()
            com = api.im.makeComment(caseNumber=self._options['casenumber'],
                                           public=self._options['public'],
                                           text=self.comment)
            retVal = api.comments.add(com)
            if retVal is None:
                print _('ERROR: There was a problem adding your comment '
                        'to %s') % self._options['casenumber']
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
            msg = _("Unable to add comment")
            print msg
            logger.log(logging.WARNING, msg)
            raise
