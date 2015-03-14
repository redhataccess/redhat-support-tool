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
from optparse import Option
from redhat_support_lib.infrastructure.errors import RequestError, \
    ConnectionError
from redhat_support_tool.helpers.confighelper import EmptyValueError, _
from redhat_support_tool.helpers.constants import Constants
from redhat_support_tool.plugins import InteractivePlugin, DisplayOption
import logging
import redhat_support_tool.helpers.apihelper as apihelper
import redhat_support_tool.helpers.common as common

__author__ = 'Spenser Shumaker <sshumake@redhat.com>'
logger = logging.getLogger("redhat_support_tool.plugins.modify_case")


class ModifyCase(InteractivePlugin):
    plugin_name = 'modifycase'
    ALL = _("Modify case")
    _submenu_opts = None
    _sections = None
    _caseNumber = None
    _case = None
    _productsAry = None

    @classmethod
    def get_usage(cls):
        '''
        The usage statement that will be printed by OptionParser.

        Example:
            - %prog -c CASENUMBER [options] <comment text here>
        Important: %prog is a OptionParser built-in.  Use it!
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
        return _('Use the \'%s\' command to modify a specific case by \
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
        return [Option('-t', '--type', dest='type',
                        help=_('the type of case'),
                        default=None),
                Option('-S', '--severity', dest='severity',
                        help=_('the severity for the case'),
                        default=None),
                Option('-s', '--status', dest='status',
                        help=_('the status for the case'),
                        default=None),
                Option('-a', '--alternative-id', dest='aid',
                        help=_('aAn alternative-id for the case'),
                        default=None),
                Option('-p', '--product', dest='product',
                        help=_('the product the case is opened against'),
                         default=None),
                Option('-v', '--version', dest='version',
                        help=_('the version of the product the case is '
                                 'opened against'),
                       default=None)]

    def get_intro_text(self):
        return _('\nType the number of the attribute to modify or \'e\' '
                 'to return to the previous menu.')

    def get_prompt_text(self):
        return _('Selection: ')

    def get_sub_menu_options(self):
        return self._submenu_opts

    def _check_case_number(self):
        msg = _("ERROR: %s requires a case number.")\
                    % self.plugin_name
        self._caseNumber = ''
        if self._args:
            self._caseNumber = ' '.join(self._args)
        elif common.is_interactive():
            line = raw_input(_('Please provide a case number (or \'q\' '
                                       'to exit): '))
            line = str(line).strip()
            if line == 'q':
                raise Exception()
            if str(line).strip():
                self._caseNumber = line
            else:
                print msg
                raise Exception(msg)
        else:
            print msg
            raise Exception(msg)

    def _check_type(self):
        if self._options['type']:
            match = False
            for casetype in common.get_types():
                if self._options['type'].lower() == casetype.lower():
                    match = True
                    self._options['type'] = casetype
                    break
            if(not match):
                msg = _("ERROR: Invalid type specified.")
                print msg
                raise Exception(msg)

    def _check_severity(self):
        if self._options['severity']:
            match = False
            for severity in common.get_severities():
                if self._options['severity'].lower() in severity.lower():
                    match = True
                    self._options['severity'] = severity
                    break
            if(not match):
                msg = _("ERROR: Invalid severity specified.")
                print msg

    def _check_status(self):
        if self._options['status']:
            match = False
            for status in common.get_statuses():
                if self._options['status'].lower() == status.lower():
                    match = True
                    self._options['status'] = status
                    break
            if(not match):
                msg = _("ERROR: Invalid status specified.")
                print msg
                raise Exception(msg)

    def _check_prod(self):
        if self._options['product']:
            self._productsAry = None

            # User supplied a product
            self._productsAry = common.get_products()

            inArray = False
            for product in self._productsAry:
                if product.get_name() == self._options['product']:
                    inArray = True
                    break
            if not inArray:
                msg = _("ERROR: Invalid product provided.")
                print msg
                raise Exception(msg)

    def _check_ver(self):
        if self._options['version']:
            versions = None
            if self._options['product'] == None:
                product = self._case.get_product()
            else:
                product = self._options['product']
            if not self._productsAry:
                self._productsAry = common.get_products()
            for prod in self._productsAry:
                if product == prod.get_name():
                    versions = prod.get_versions()
                    break

            if not self._options['version'] in versions:
                msg = _("ERROR: Invalid version provided.")
                print msg
                raise Exception(msg)

    def validate_args(self):
        # Check for required arguments.
        self._check_case_number()
        self._check_type()
        self._check_severity()
        self._check_status()
        self._check_prod()

    def postinit(self):
        self._submenu_opts = deque()
        self._sections = {}
        api = None
        try:
            api = apihelper.get_api()
            self._case = api.cases.get(self._caseNumber)
            # Case needs to be retrieved before check version.
            # Product needs to be retrieved to check version
            self._check_ver()

            self._createDisplayOpts()
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
            msg = _("Problem updating case")
            print msg
            logger.log(logging.WARNING, msg)
            raise

    def _createDisplayOpts(self):
        # Modify Type
        disp_opt = DisplayOption(Constants.CASE_MODIFY_TYPE,
                                     'interactive_action')
        self._submenu_opts.append(disp_opt)
        self._sections[disp_opt] = Constants.CASE_MODIFY_TYPE

        # Modify Severity
        disp_opt = DisplayOption(Constants.CASE_MODIFY_SEVERITY,
                                     'interactive_action')
        self._submenu_opts.append(disp_opt)
        self._sections[disp_opt] = Constants.CASE_MODIFY_SEVERITY

        # Modify Status
        disp_opt = DisplayOption(Constants.CASE_MODIFY_STATUS,
                                     'interactive_action')
        self._submenu_opts.append(disp_opt)
        self._sections[disp_opt] = Constants.CASE_MODIFY_STATUS

        # Modify Alternative ID
        disp_opt = DisplayOption(Constants.CASE_MODIFY_AID,
                                     'interactive_action')
        self._submenu_opts.append(disp_opt)
        self._sections[disp_opt] = Constants.CASE_MODIFY_AID

        # Modify Product
        disp_opt = DisplayOption(Constants.CASE_MODIFY_PROD,
                                     'interactive_action')
        self._submenu_opts.append(disp_opt)
        self._sections[disp_opt] = Constants.CASE_MODIFY_PROD

        # Modify Version
        disp_opt = DisplayOption(Constants.CASE_MODIFY_VER,
                                     'interactive_action')
        self._submenu_opts.append(disp_opt)
        self._sections[disp_opt] = Constants.CASE_MODIFY_VER

    def non_interactive_action(self):
        if self._options['type']:
            self._case.set_type(self._options['type'])
        if self._options['severity']:
            self._case.set_severity(self._options['severity'])
        if self._options['status']:
            self._case.set_status(self._options['status'])
        if self._options['aid']:
            self._case.set_alternateId(self._options['aid'])
        if self._options['product']:
            self._case.set_product(self._options['product'])
        if self._options['version']:
            self._case.set_version(self._options['version'])
        self._case.update()

    def interactive_action(self, display_option=None):
        if display_option.display_text == Constants.CASE_MODIFY_TYPE:
            if self._get_type():
                self._case.set_type(self._options['type'])
                self._case.update()
                print _("Successfully updated case %s") % \
                    self._case.get_caseNumber()
        elif display_option.display_text == Constants.CASE_MODIFY_SEVERITY:
            if self._get_severity():
                self._case.set_severity(self._options['severity'])
                self._case.update()
                print _("Successfully updated case %s") % \
                    self._case.get_caseNumber()
        elif display_option.display_text == Constants.CASE_MODIFY_STATUS:
            if self._get_status():
                self._case.set_status(self._options['status'])
                self._case.update()
                print _("Successfully updated case %s") % \
                    self._case.get_caseNumber()
        elif display_option.display_text == Constants.CASE_MODIFY_AID:
            if self._get_aid():
                self._case.set_alternateId(self._options['aid'])
                self._case.update()
                print _("Successfully updated case %s") % \
                    self._case.get_caseNumber()
        elif display_option.display_text == Constants.CASE_MODIFY_PROD:
            if self._get_prod():
                if (self._options['product'] != self._case.get_product() and
                    self._get_ver()):
                    # We may need to update the product version if the product
                    # changes.
                    # Least we get 403 errors!
                    self._case.set_version(self._options['version'])
                self._case.set_product(self._options['product'])
                self._case.update()
                print _("Successfully updated case %s") % \
                    self._case.get_caseNumber()
        elif display_option.display_text == Constants.CASE_MODIFY_VER:
            if self._get_ver():
                self._case.set_version(self._options['version'])
                self._case.update()
                print _("Successfully updated case %s") % \
                    self._case.get_caseNumber()

    def _get_type(self):
        typesAry = common.get_types()
        common.print_types(typesAry)
        while True:
            line = raw_input(_('Please select a type (or \'q\' '
                                   'to exit): '))
            if str(line).strip() == 'q':
                return False
            try:
                line = int(line)
            # pylint: disable=W0702
            except:
                print _("ERROR: Invalid type selection.")
            if line in range(1, len(typesAry) + 1) and line != '':
                self._options['type'] = typesAry[line - 1]
                break
            else:
                print _("ERROR: Invalid type selection.")
        return True

    def _get_severity(self):
        severitiesAry = common.get_severities()
        common.print_severities(severitiesAry)
        while True:
            line = raw_input(_('Please select a severity (or \'q\' '
                                           'to exit): '))
            if str(line).strip() == 'q':
                return False
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
        return True

    def _get_status(self):
        statusesAry = common.get_statuses()
        common.print_statuses(statusesAry)

        while True:
            line = raw_input(_('Please select a status (or \'q\' '
                                       'to exit): '))
            if str(line).strip() == 'q':
                return False
            try:
                line = int(line)
            # pylint: disable=W0702
            except:
                print _("ERROR: Invalid status selection.")
            if line in range(1, len(statusesAry) + 1) and line != '':
                self._options['status'] = statusesAry[line - 1]
                break
            else:
                print _("ERROR: Invalid status selection.")
        return True

    def _get_aid(self):
        while True:
            line = raw_input(_('Please provide a alternative-id (or \'q\' '
                                           'to exit): '))
            line = str(line).strip()
            if line == 'q':
                return False
            if line != '':
                self._options['aid'] = line
                break
            else:
                print _("ERROR: Invalid alternative-id provided.")
        return True

    def _get_prod(self):
        self._productsAry = common.get_products()
        common.print_products(self._productsAry)
        while True:
            line = raw_input(_('Please select a product (or \'q\' '
                                       'to exit): '))
            if str(line).strip() == 'q':
                return False
            try:
                line = int(line)
            # pylint: disable=W0702
            except:
                print _("ERROR: Invalid product selection.")
            if line in range(1, len(self._productsAry) + 1) and line != '':
                self._options['product'] = self._productsAry[line - 1]\
                    .get_name()
                break
            else:
                print _("ERROR: Invalid product selection.")
        return True

    def _get_ver(self):

        versions = None
        if self._options['product'] == None:
            self._options['product'] = self._case.get_product()
        if(not self._productsAry):
            self._productsAry = common.get_products()
        for product in self._productsAry:
            if self._options['product'] == product.get_name():
                versions = product.get_versions()
                break

        common.print_versions(versions)
        while True:
            line = raw_input(_('Please select a version (or \'q\' '
                                       'to exit): '))
            if str(line).strip() == 'q':
                return False
            try:
                line = int(line)
            # pylint: disable=W0702
            except:
                print _("ERROR: Invalid version selection.")
            if line in range(1, len(self._productsAry) + 1) and line != '':
                self._options['version'] = versions[line - 1]
                break
            else:
                print _("ERROR: Invalid version selection.")
        return True
