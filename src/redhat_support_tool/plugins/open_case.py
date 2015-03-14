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
from redhat_support_lib.infrastructure.errors import RequestError, \
    ConnectionError
from redhat_support_tool.helpers.confighelper import EmptyValueError, _
from redhat_support_tool.helpers.launchhelper import LaunchHelper
from redhat_support_tool.helpers.constants import Constants
from redhat_support_tool.helpers.genericinteractiveprompt import GenericPrompt
from redhat_support_tool.plugins import Plugin
from redhat_support_tool.plugins.add_attachment import AddAttachment
import os
import redhat_support_tool.helpers.apihelper as apihelper
import redhat_support_tool.helpers.common as common
import redhat_support_tool.helpers.recommendationprompter as \
                                        recommendationprompter
import subprocess as sub
import logging
import sys


__author__ = 'Spenser Shumaker <sshumake@redhat.com>'
logger = logging.getLogger("redhat_support_tool.plugins.add_case")


class OpenCase(Plugin):
    plugin_name = 'opencase'
    comment = None
    attachment = None
    _productsAry = None
    _caseNumber = None

    @classmethod
    def get_usage(cls):
        '''
        The usage statement that will be printed by OptionParser.

        Example:
            - %prog -c CASENUMBER [options] <comment text here>
        Important: %prog is a OptionParser built-in.  Use it!
        '''
        return _('%prog -s SUMMARY -p PRODUCT -v VERSION -d DESCRIPTION '
                 '[options]')

    @classmethod
    def get_desc(cls):
        '''
        The description statement that will be printed by OptionParser.

        Example:
            - 'Use the \'%s\' command to add a comment to a case.'\
             % cls.plugin_name
        '''
        return _('Use the \'%s\' command to open a new support case.')\
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
  - %s -s Summary -p Red Hat Enterprise Virtualization -v 3.0 -d description
""") % (cls.plugin_name)

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
        return [Option('-p', '--product', dest='product',
                        help=_('The product the case will be opened against. '
                                '(required)'), default=None),
                Option('-v', '--version', dest='version',
                        help=_('The version of the product the case '
                                'will be opened against. (required)'),
                       default=None),
                Option('-s', '--summary', dest='summary',
                        help=_('A summary for the case (required)'),
                        default=None),
                Option('-d', '--description', dest='description',
                        help=_('A description for the case. (required)'),
                        default=None),
                Option('-S', '--severity', dest='severity',
                        help=_('The severity of the case. (optional)'),
                        default=None),
                Option('-a', '--attachment', dest='attachment',
                        help=_('Add an attachment to the newly opened case. '
                               '(optional)'),
                        default=None),
                Option('-g', '--casegroup', dest='casegroup',
                        help=_('Add this case to the designated case group. '
                               '(optional)'),
                        default=None)]

    def _check_product(self):
        msg = _("ERROR: %s requires a product.")\
                    % self.plugin_name
        self._productsAry = None
        beenVerified = False
        if not self._options['product']:
            if common.is_interactive():
                self._productsAry = common.get_products()
                common.print_products(self._productsAry)
                while True:
                    line = raw_input(_('Please select a product (or \'q\' '
                                       'to exit): '))
                    if str(line).strip() == 'q':
                        raise Exception()
                    try:
                        line = int(line)
                    # pylint: disable=W0702
                    except:
                        print _("ERROR: Invalid product selection.")
                        continue
                    if line in range(1, len(self._productsAry) + 1) and \
                            line != '':
                        self._options['product'] = self._productsAry[line - 1]\
                            .get_name()
                        beenVerified = True
                        break
                    else:
                        print _("ERROR: Invalid product selection.")
            else:
                print msg
                raise Exception(msg)
        else:
            # User supplied a product
            self._productsAry = common.get_products()

        if not beenVerified:
            inArray = False
            for product in self._productsAry:
                if product.get_name().lower() == self._options['product'].\
                        lower():
                    inArray = True
                    self._options['product'] = product.get_name()
                    break
            if not inArray:
                msg = _("ERROR: Invalid product provided.")
                print msg
                raise Exception(msg)

    def _check_version(self):
        msg = _("ERROR: %s requires a version.") \
                % self.plugin_name

        beenVerified = False
        versions = None
        for product in self._productsAry:
            if self._options['product'] == product.get_name():
                versions = product.get_versions()
                break

        if not self._options['version']:
            if common.is_interactive():
                common.print_versions(versions)
                while True:
                    line = raw_input(_('Please select a version (or \'q\' '
                                       'to exit): '))
                    if str(line).strip() == 'q':
                        raise Exception()
                    try:
                        line = int(line)
                    # pylint: disable=W0702
                    except:
                        print _("ERROR: Invalid version selection.")
                        continue

                    if line in range(1, len(versions) + 1) and line != '':
                        self._options['version'] = versions[line - 1]
                        beenVerified = True
                        break
                    else:
                        print _("ERROR: Invalid version selection.")
            else:
                print msg
                raise Exception(msg)

        if not beenVerified:
            inArray = False
            for version in versions:
                if version.lower() == self._options['version'].lower():
                    inArray = True
                    self._options['version'] = version
                    break
            if not inArray:
                msg = _("ERROR: Invalid version provided.")
                print msg
                raise Exception(msg)

    def _check_summary(self):
        msg = _("ERROR: %s requires a summary.")\
                    % self.plugin_name

        if not self._options['summary']:
            if common.is_interactive():
                while True:
                    line = raw_input(_('Please enter a summary (or \'q\' '
                                       'to exit): '))
                    try:
                        line = str(line).strip()
                    # pylint: disable=W0702
                    except:
                        print _("ERROR: Invalid summary selection.")
                    if str(line).strip() == 'q':
                        raise Exception()
                    if(line == ''):
                        print _("ERROR: Invalid summary selection.")
                    else:
                        self._options['summary'] = line
                        break
            else:
                print msg
                raise Exception(msg)

    def _check_description(self):
        msg = _("ERROR: %s requires a description.")\
                    % self.plugin_name

        if not self._options['description']:
            if common.is_interactive():
                while True:
                    userinput = []
                    try:
                        print _('Please enter a description (Ctrl-D on an'
                                ' empty line when complete):')
                        while True:
                            userinput.append(raw_input())
                    except EOFError:
                        # User pressed Ctrl-d
                        description = str('\n'.join(userinput)).strip()
                        if description == '':
                            print _("ERROR: Invalid description.")
                        else:
                            self._options['description'] = description.decode(
                                                                    'utf_8')
                            break
            else:
                print msg
                raise Exception(msg)

    def _check_severity(self):
        msg = _("ERROR: Invalid severity selection")
        if not self._options['severity']:
            if common.is_interactive():
                severitiesAry = common.get_severities()
                common.print_severities(severitiesAry)
                while True:
                    line = raw_input(_('Please select a severity (or \'q\' '
                                       'to exit): '))
                    if str(line).strip() == 'q':
                        raise Exception()
                    try:
                        line = int(line)
                    # pylint: disable=W0702
                    except:
                        print _("ERROR: Invalid severity selection.")

                    if line in range(1, len(severitiesAry) + 1) and line != '':
                        self._options['severity'] = severitiesAry[line - 1]
                        break
                    else:
                        print _("ERROR: Invalid severity selection.")
        else:
            match = False
            for severity in common.get_severities():
                if self._options['severity'].lower() in severity.lower():
                    match = True
                    self._options['severity'] = severity
                    break
            if(not match):
                msg = _("ERROR: Invalid severity specified.")
                print msg

    def _check_case_group(self):
        msg = _("ERROR: Invalid case group selection")
        if not self._options['casegroup']:
            if common.is_interactive():
                line = raw_input(_('Would you like to assign a case'
                                   ' group to this case (y/N)? '))
                if str(line).strip().lower() == 'y':
                    groupsAry = common.get_groups()
                    common.print_groups(groupsAry)
                    while True:
                        line = raw_input(_('Please select a severity (or \'q\' '
                                           'to exit): '))
                        if str(line).strip() == 'q':
                            raise Exception()
                        try:
                            line = int(line)
                        # pylint: disable=W0702
                        except:
                            print _("ERROR: Invalid severity selection.")

                        if line in range(1, len(groupsAry) + 1) and line != '':
                            self._options['casegroup'] = groupsAry[line - 1]
                            self._options['casegroupnumber'] = \
                                    groupsAry[line - 1].get_number()
                            logger.log(logging.INFO,
                                       'Casegroup(%s) casegroupnumber(%s)' % (
                                       self._options['casegroup'].get_name(),
                                       self._options['casegroupnumber']))
                            break
                        else:
                            print _("ERROR: Invalid case group selection.")
        else:
            match = False
            for group in common.get_groups():
                if self._options['casegroup'].lower() in \
                                        group.get_name().lower():
                    match = True
                    self._options['casegroup'] = group.get_name()
                    self._options['casegroupnumber'] = group.get_number()
                    logger.log(logging.INFO,
                               'Casegroup(%s) casegroupnumber(%s)' % (
                               self._options['casegroup'],
                               self._options['casegroupnumber']))
                    break
            if(not match):
                msg = _("ERROR: Invalid case group specified.")
                print msg

    def validate_args(self):
        self._check_product()
        self._check_version()
        self._check_summary()
        self._check_description()
        self._check_severity()
        self._check_case_group()

    def non_interactive_action(self):
        api = None
        try:
            api = apihelper.get_api()

            case = api.im.makeCase()
            case.summary = self._options['summary']
            case.product = self._options['product']
            case.version = self._options['version']
            case.description = self._options['description']
            case.severity = self._options['severity']
            if self._options['casegroup']:
                case.folderNumber = self._options['casegroupnumber']

            if common.is_interactive():
                line = raw_input(_('Would see if there is a solution to this '
                            'problem before opening a support case? (y/N) '))
                line = str(line).strip().lower()
                if line == 'y':
                    recommendations = api.problems.diagnoseCase(case)
                    recprompt, recdoc = \
                        recommendationprompter.generate_metadata(
                                                            recommendations)
                    lh = LaunchHelper(GenericPrompt)
                    lh.run('', recprompt, prompt=_(\
                           'Selection (q returns to case creation menu): '))
                    line = raw_input(\
                                _('Would you still like to open the support'
                                  ' case? (Y/n) '))
                    if line.lower() == 'n':
                        print _('Thank you for using Red Hat Access')
                        return

            cs = api.cases.add(case)
            if cs.get_caseNumber() is None:
                msg = _("ERROR: There was a problem creating your case.")
                print msg
                raise Exception(msg)
            self._caseNumber = cs.get_caseNumber()
            print '%s%s%s' % (Constants.BOLD,
                                      str('-' * Constants.MAX_RULE),
                                      Constants.END)
            msg = _("Support case %s has successfully been opened.\n") % \
                self._caseNumber
            print msg
            logger.log(logging.INFO, msg)

            # Attach a file
            if self._options['attachment']:
                lh = LaunchHelper(AddAttachment)
                lh.run('-c %s -d \'[RHST] File %s \' %s' % (
                                self._caseNumber,
                                os.path.basename(self._options['attachment']),
                                self._options['attachment']))
            elif (os.geteuid() == 0):
                sys.stdout.write(_(
    'Would you like Red Hat Support Tool to automatically generate and\n'
    'attach a SoS report to %s now? (y/N) ') % (self._caseNumber))
                line = raw_input()

                line = str(line).strip()
                if line == 'y':
                    # retval = os.system('sosreport')
                    p = sub.Popen(['sosreport', '--batch'],
                                  stdout=sub.PIPE, stderr=sub.STDOUT)
                    output = p.communicate()[0].split('\n')
                    for out in output:
                        if '.tar.' in out:
                            path = str(out).strip()
                            lh = LaunchHelper(AddAttachment)
                            lh.run('-c %s %s' % (self._caseNumber, path))
                            break
            else:
                print _(
   'Please attach a SoS report to support case %s. Create a SoS report as\n'
   'the root user and execute the following command to attach the SoS report\n'
   'directly to the case:\n'
   ' redhat-support-tool addattachment -c %s <path to sosreport>\n') % \
    (self._caseNumber, self._caseNumber)

            if not self._options['attachment']:
                line = raw_input(_('Would you like to attach a file to %s '
                                   'at this time? (y/N) ') % self._caseNumber)
                line = str(line).strip()
                if line == 'y':
                    lh = LaunchHelper(AddAttachment)
                    lh.run('-c %s' % (self._caseNumber))
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
            msg = _("Unable to create case.")
            print msg
            logger.log(logging.WARNING, msg)
            raise
