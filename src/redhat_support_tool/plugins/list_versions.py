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
from redhat_support_tool.plugins import Plugin
import redhat_support_tool.helpers.common as common
from redhat_support_tool.helpers.confighelper import _
from redhat_support_tool.helpers.common import get_products

__author__ = 'Spenser Shumaker <sshumake@redhat.com>'


class ListVersions(Plugin):
    plugin_name = 'listversions'
    ALL = _("Display all versions")

    @classmethod
    def get_usage(cls):
        '''
        The usage statement that will be printed by OptionParser.

        Example:
            - %prog -c CASENUMBER [options] <comment text here>
        Important: %prog is a OptionParser built-in.  Use it!
        '''
        return _('%prog -p PRODUCT')

    @classmethod
    def get_desc(cls):
        '''
        The description statement that will be printed by OptionParser.

        Example:
            - 'Use the \'%s\' command to add a comment to a case.'\
             % cls.plugin_name
        '''
        return _('Use the \'%s\' command to list versions of a product.')\
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
                 '- %s Red Hat Enterprise Linux') % (cls.plugin_name)

    def _check_product(self):
        msg = _("ERROR: %s requires a product.")\
                    % self.plugin_name

        if not self._line:
            if common.is_interactive():
                line = raw_input(_('Please provide the product (or \'q\' '
                                       'to exit): '))
                line = str(line).strip()
                if line == 'q':
                    raise Exception()
                self._line = line
            else:
                print msg
                raise Exception(msg)

    def validate_args(self):
        self._check_product()

    def non_interactive_action(self):
        msg = _("ERROR: Invalid product provided.")

        prodAry = get_products()
        if prodAry:
            inArray = False
            for product in prodAry:
                if product.get_name().lower() == self._line.lower():
                    inArray = True
                    for version in product.get_versions():
                        print version
                    break
            if not inArray:
                print msg
                raise Exception(msg)
        else:
            print msg
            raise Exception(msg)
