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
from fnmatch import fnmatch
from optparse import Option
from redhat_support_tool.helpers import common
from redhat_support_tool.helpers.confighelper import _
from redhat_support_tool.helpers.vmcorehelper import list_extracted_vmlinuxes
from redhat_support_tool.plugins import InteractivePlugin, DisplayOption
import logging
import os
import redhat_support_tool.helpers.confighelper as confighelper
import shutil


__author__ = 'Nigel Jones <nigjones@redhat.com>'
__author__ = 'Keith Robertson <kroberts@redhat.com>'
logger = logging.getLogger("redhat_support_tool.plugins.rmkerneldebug")


class RemKernelDebugs(InteractivePlugin):
    plugin_name = 'rmkerneldebug'

    partial_entries = _('%s of %s vmlinux images displayed. Type \'m\' to'
                        ' see more, or \'r\' to start from the beginning'
                        ' again.')
    end_of_entries = _('No more vmlinux images to display.')

    _submenu_opts = None

    @classmethod
    def get_usage(cls):
        '''
        The usage statement that will be printed by OptionParser.

        Example:
            - %prog -c CASENUMBER [options] <comment text here>
        Important: %prog is a OptionParser built-in.  Use it!
        '''
        return _('%prog [--noprompt] <kerneldebugname>')

    @classmethod
    def get_desc(cls):
        '''
        The description statement that will be printed by OptionParser.

        Example:
            - 'Use the \'%s\' command to add a comment to a case.'\
             % cls.plugin_name
        '''
        return _('Use the \'%s\' command to remove currently downloaded debug '
                 'vmlinux images.') % \
                 cls.plugin_name

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
        return _("""Example:
  - %s kernel-debuginfo-2.6.18-128*""") \
  % (cls.plugin_name)

    @classmethod
    def get_options(cls):
        return [Option("-n", "--noprompt", dest="noprompt",
                    action="store_true",
                    help=_('Does not prompt for confirmation.'),
                    default=False)]

    def validate_args(self):
        if not common.is_interactive():
            msg = _("ERROR: %s requires search string for deletion.")\
                        % self.plugin_name

            if not self._line:
                print msg
                raise Exception(msg)

    def get_intro_text(self):
        return _('\nType the number of a vmlinux image to delete '
                 'or \'e\' to return to the previous menu.')

    def get_prompt_text(self):
        return _('Select an image: ')

    def get_sub_menu_options(self):
        return self._submenu_opts

    def postinit(self):
        kernelext_dir = confighelper.get_config_helper().get(
                                            option='kern_debug_dir')
        self._submenu_opts = deque()
        searchopts = []
        kernels = list_extracted_vmlinuxes(kernelext_dir)
        results = []

        if common.is_interactive() and self._line == '':
            searchopts.append("*")
        else:
            searchopts = self._line.split()

        # itertools.product() would be a good option here, but not supported in
        # python 2.4
        for kernel in kernels:
            for search in searchopts:
                if fnmatch(kernel, search):
                    results.append(kernel)

        # Make the results unique, and process options
        for option in results:
            self._submenu_opts.append(DisplayOption(option,
                                                    'interactive_action'))

    def non_interactive_action(self):
        if len(self._submenu_opts) == 0:
            print _('No images to remove.')
            return

        doc = u''
        doc += _('The following kernels will be removed:\n')
        for image in self._submenu_opts:
            doc += image.display_text
            try:
                print doc.encode("UTF-8", 'replace')
            # pylint: disable=W0703
            except Exception, e:
                # There are some truly bizarre errors when you pipe
                # the output from python's 'print' function with sys encoding
                # set to ascii. These errors seem to manifes when you pipe
                # to something like 'more' or 'less'.  You'll get encoding
                # errors. Curiously, you don't see them with 'grep' or even
                # simply piping to terminal.  WTF :(
                logger.log(logging.WARNING, e)
                import sys
                print doc.encode(sys.getdefaultencoding(),
                                   'replace')
            doc = u''

        if not self._options['noprompt']:
            line = raw_input(_('Are you sure you wish to remove the above '
                    'vmlinux images (y/n)? '))
            if str(line).strip().lower() != 'y':
                return

        self._do_delete(self._submenu_opts)

    def interactive_action(self, display_option=None):
        if display_option:
            self._do_delete([display_option])
        else:
            raise Exception()

    def _do_delete(self, deleteque=None):
        res = self._delete_vmlinuxes(deleteque)

        if len(res) > 0:
            print _('The following vmlinux images were unable to be removed:')
            for kernel in res:
                print _(' - %s' % (kernel))
        else:
            print _('The vmlinux images were successfully removed.')

    def _delete_vmlinuxes(self, deleteque=None):
        if not deleteque:
            raise Exception()

        failedkernels = []

        kernelext_dir = confighelper.get_config_helper().get(
                                            option='kern_debug_dir')

        for kernel in deleteque:
            kpath = os.path.join(kernelext_dir, kernel.display_text)
            if kpath != kernelext_dir and os.path.exists(kpath):
                try:
                    shutil.rmtree(kpath)
                # pylint: disable=W0702
                except:
                    failedkernels.append(kernel.display_text)

        return failedkernels
