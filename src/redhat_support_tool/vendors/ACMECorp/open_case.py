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
from redhat_support_tool.plugins import Plugin
from redhat_support_tool.plugins.open_case import OpenCase
import os
import logging
import sys


__author__ = 'ACME Developer <developer@example.com>'
logger = logging.getLogger("redhat_support_tool.vendors.ACMECorp.open_case")


class OpenACMECase(Plugin):
    plugin_name = 'newacmecase'
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
        return _('Open a case directly with ACME Corp for systems with'
                 ' bundled support subscriptions')

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
                        default=None)]

    def validate_args(self):
        pass

    def non_interactive_action(self):
        print _('This is the ACMECorp RHEL Support Helper Example')


class OpenDirectCase(OpenCase):
    plugin_name = 'newredhatcase'

    @classmethod
    def get_desc(cls):
        '''
        The description statement that will be printed by OptionParser.

        Example:
            - 'Use the \'%s\' command to add a comment to a case.'\
             % cls.plugin_name
        '''
        return _('Open a case directly with Red Hat for products purchased'
                 ' separately from your system.')
