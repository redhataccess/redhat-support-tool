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
from redhat_support_lib.infrastructure import contextmanager
from redhat_support_tool.helpers.confighelper import _
from redhat_support_tool.helpers.confighelper import EmptyValueError
from redhat_support_tool.plugins import InteractivePlugin, ObjectDisplayOption
from redhat_support_tool.helpers.constants import Constants
from redhat_support_tool.helpers.launchhelper import LaunchHelper
from redhat_support_tool.plugins.get_case import GetCase
import pydoc
import redhat_support_tool.helpers.common as common
import redhat_support_tool.helpers.apihelper as apihelper
import redhat_support_tool.helpers.confighelper as confighelper
import logging

__author__ = 'Keith Robertson <kroberts@redhat.com>'
logger = logging.getLogger("redhat_support_tool.plugins.list_cases")


class ListCases(InteractivePlugin):
    plugin_name = 'listcases'
    ALL = _("Display all cases")
    partial_entries = _('%s of %s cases displayed. Type \'m\' to see more.')
    end_of_entries = _('No more cases to display')

    _submenu_opts = None
    _sections = None
    casesAry = None

    # Help should not print the option list
    help_is_options = False

    # Record the last offset value used with the API, and the maximum results
    # we should display for one search query.
    _nextOffset = 0
    _MAX_OFFSET = confighelper.get_config_helper().get(option='max_results')
    _MAX_OFFSET = 1500 if not _MAX_OFFSET else int(_MAX_OFFSET)
    _limit = 50 if _MAX_OFFSET >= 50 else _MAX_OFFSET

    _caseGroupNumbers = None
    # for displaying cases owned by an associate as per SFDC
    _associateSSOName = None
    _view = None

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
        return _('Use the \'%s\' command to list your open support cases.\n'
                 '- For Red Hat employees it lists open cases in your queue.\n'
                 '- For other users it lists open cases in your account.\n'
                 % cls.plugin_name)

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
                 '  - %s\n'
                 '  - %s -g groupname -c -s status -a\n'
                 '  - %s -o ownerSSOName -s severity\n'
                 '  - %s -o all') % (cls.plugin_name,
                                     cls.plugin_name,
                                     cls.plugin_name,
                                     cls.plugin_name)

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
        return [Option('-c', '--includeclosed', dest='includeclosed',
                       action='store_true',
                       help=_('Show closed cases. (optional)'), default=False),
                Option('-o', '--owner', dest='owner',
                        help=_('For Red Hat employees only.  Show cases '
                               'for another Red Hat employee portal login ID.'
                               '  Specify -o ALL to show cases in the Red Hat '
                               'account instead of your case queue. (optional)'
                               ), default=None),
                Option('-g', '--casegroup', dest='casegroup',
                        help=_('Show cases belonging to a particular case group'
                               ' in your account. (optional)  Note, use the '
                               '\'listcasegroups\' command to see the case '
                               'groups in your account.'), default=None),
                #Option('-k', '--keyword', dest='keyword',
                #        help=_('Only show cases with the given keyword in '
                #               'their title. (optional)'), default=None),
                Option('-u', '--ungrouped', dest='ungrouped',
                       action='store_true',
                       help=_('Include ungrouped cases in results. When this '
                              'is set then -o owner options will be ignored.'
                              '(optional)'), default=False),
                Option('-s', '--sortby', dest='sortfield',
                        help=_("Sort cases by a particular field.  Available "
                               "fields to sort by are: 'caseNumber' (default), "
                               "'createdDate', 'lastModifiedDate', 'severity', "
                               "'status'. (optional)"), default='caseNumber'),
                Option('-a', '--ascending', dest='sortorder',
                                action='store_const', const='ASC',
                        help=_('Sort results in ascending order.  Default is '
                               'to sort in descending order (optional)'),
                               default='DESC')]

    def _check_case_group(self):
        if self._options['casegroup']:
            valid_groups = []
            given_groupAry = str(self._options['casegroup']).split(',')
            real_groupAry = common.get_groups()

            for i in given_groupAry:
                match = False
                for j in real_groupAry:
                    if i.lower() == j.get_name().lower() or \
                       i == str(j.get_number()):
                        valid_groups.append(j.get_number())
                        match = True
                if(not match):
                    msg = _("Unable to find case group %s" % i)
                    print msg
                    raise Exception(msg)

            if len(valid_groups) > 0:
                self._caseGroupNumbers = valid_groups

            logger.log(logging.INFO,
                       'Casegroup(%s) casegroupnumber(%s)' % (
                       given_groupAry,
                       self._caseGroupNumbers))

    def _check_owner(self):
        # Firstly, determine for whom listcases is being run and if they're a
        #    Red Hat employee (isInternal == True) or not
        # If they're internal, then display the open cases they *own* in SFDC
        # ...except however if the -o all, -g or -u options are specified, then
        #    it displays cases in the Red Hat employee's account.
        # If they're not internal, then display the open cases in their account

        try:
            api = apihelper.get_api()
            username = api.config.username

            userobj = contextmanager.get('user')
            if not userobj:
                userobj = api.users.get(username)
                contextmanager.add('user', userobj)

            if self._options['owner']:
                if not userobj.isInternal:
                    raise Exception("The -o switch is only available to Red Hat"
                                    " employees")
                elif self._options['owner'].lower() != 'all':
                    username = self._options['owner']
                    userobj = api.users.get(username)
                    if not userobj.isInternal:
                        # for some reason RH users can't display non-RH users
                        raise Exception("Red Hat employees are unable to list"
                                        "cases for non-Red Hat portal users.")

            if userobj.isInternal:
                if not (str(self._options['owner']).lower() == 'all' or
                        self._caseGroupNumbers or
                        self._options['ungrouped']):
                    # this will trigger the display of cases owned as per SFDC
                    self._associateSSOName = username
                    self._view = 'internal'

        except RequestError, re:
            if re.status == 404:
                msg = _("Unable to find user %s" % username)
            else:
                msg = _('Problem querying the support services API.  Reason: '
                        '%s' % re.reason)
            print msg
            logger.log(logging.WARNING, msg)
            raise
        except ConnectionError:
            msg = _('Problem connecting to the support services API.  '
                    'Is the service accessible from this host?')
            print msg
            logger.log(logging.WARNING, msg)
            raise
        except Exception, e:
            msg = _("%s" % str(e))
            print msg
            logger.log(logging.WARNING, msg)
            raise

    def validate_args(self):
        self._check_case_group()
        self._check_owner()

    def get_intro_text(self):
        return _('\nType the number of the case to view or \'e\' '
                 'to return to the previous menu.')

    def get_prompt_text(self):
        return _('Select a Case: ')

    def get_sub_menu_options(self):
        return self._submenu_opts

    def get_more_options(self, num_options):
        if (len(self.casesAry) < self._nextOffset or
            len(self.casesAry) == 0 or
            self._nextOffset > self._MAX_OFFSET):
            # Either we did not max out on results last time, there were
            # no results last time, or we have seen more than _MAX_OFFSET
            # results.
            # In the instance of cases, the maximum a single query can
            # retrieve is 1500 cases, hence MAX_OFFSET is set to 1450
            return False

        # Strata introduces an issue where if the limit > 50, it will only
        # return 50 results. This creates a potential issue if the terminal
        # size is greater than 53.
        limit = self._get_limit()
        if num_options > limit:
            num_options = limit

        searchopts = {'count': num_options, 'start': self._nextOffset}
        self._nextOffset += num_options
        newresults = self._get_cases(searchopts)

        if len(newresults) == 0:
            return False

        self.casesAry.extend(newresults)
        self._parse_cases(newresults)
        return True

    def postinit(self):
        self._submenu_opts = deque()
        self._sections = {}

        searchopts = {'count': self._limit, 'start': 0}
        self.casesAry = self._get_cases(searchopts)
        self._nextOffset = self._limit

        if not self._parse_cases(self.casesAry):
            msg = _("Unable to find cases")
            print msg
            logger.log(logging.WARNING, msg)
            raise Exception()

        if not common.is_interactive():
            while self.get_more_options(self._limit):
                continue

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
            val = None
            try:
                val = display_option.stored_obj
                lh = LaunchHelper(GetCase)
                lh.run(val)
            except:
                raise Exception()

    def _parse_cases(self, cases_ary):
        '''
        Use this for non-interactive display of results.
        '''
        if len(cases_ary) == 0:
            return False

        try:
            for val in cases_ary:
                doc = u''
                doc += '%-12s %-60s\n' % ('%s:' % Constants.CASE_NUMBER,
                                           val.get_caseNumber())
                doc += '%-12s %-60s\n' % ('%s:' % Constants.TITLE,
                                           val.get_summary())
                doc += '%-12s %-60s\n' % (Constants.CASE_STATUS,
                                           val.get_status())
                doc += '%-12s %-60s\n' % (Constants.CASE_SEVERITY,
                                           val.get_severity())
                vuri = val.get_view_uri()
                if vuri:
                    doc += '%-12s %-60s' % (Constants.URL, vuri)
                else:
                    doc += '%-12s %-60s' % (Constants.URL, val.get_uri())
                doc += '\n\n%s%s%s\n\n' % (Constants.BOLD,
                                           str('-' * Constants.MAX_RULE),
                                           Constants.END)
                disp_opt = ObjectDisplayOption('%s [%-19s] [sev%s] %s' % (
                                                val.get_caseNumber(),
                                                val.get_status(),
                                                val.get_severity()[0],
                                                val.get_summary()),
                                                'interactive_action',
                                                val.get_caseNumber())
                self._submenu_opts.append(disp_opt)
                self._sections[disp_opt] = doc
        except:
            msg = _('ERROR: problem parsing the cases.')
            print msg
            logger.log(logging.WARNING, msg)
            return False
        return True

    def _get_cases(self, searchopts):
        api = None
        try:
            api = apihelper.get_api()
            filt = api.im.makeCaseFilter(
                            count=searchopts['count'],
                            start=searchopts['start'],
                            includeClosed=self._options['includeclosed'],
                            groupNumbers=self._caseGroupNumbers,
                            associateSSOName=self._associateSSOName,
                            view=self._view,
                            sortField=self._options['sortfield'],
                            sortOrder=self._options['sortorder'],
                            #keyword=self._options['keyword'],
                            onlyUngrouped=self._options['ungrouped'])
            return api.cases.filter(filt)

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
            msg = _("Unable to find cases")
            print msg
            logger.log(logging.WARNING, msg)
            raise

    def _get_limit(self):
        limit = self._limit
        remaining = self._MAX_OFFSET - self._nextOffset
        return limit if remaining >= limit else remaining % limit
