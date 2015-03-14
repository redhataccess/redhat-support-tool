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
from redhat_support_tool.helpers.confighelper import _
from redhat_support_tool.helpers.vmcorehelper import VMLinux, \
    list_extracted_vmlinuxes
from redhat_support_tool.plugins import InteractivePlugin, DisplayOption
import logging
import os
import redhat_support_tool.helpers.confighelper as confighelper


__author__ = 'Nigel Jones <nigjones@redhat.com>'
__author__ = 'Keith Robertson <kroberts@redhat.com>'
logger = logging.getLogger("redhat_support_tool.plugins.listkerneldebugs")


class ListKernelDebugs(InteractivePlugin):
    plugin_name = 'listkerneldebugs'

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
        return _('%prog')

    @classmethod
    def get_desc(cls):
        '''
        The description statement that will be printed by OptionParser.

        Example:
            - 'Use the \'%s\' command to add a comment to a case.'\
             % cls.plugin_name
        '''
        return _('Use the \'%s\' command to list currently downloaded debug '
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
        return _("""Examples:
  - %s""") \
  % (cls.plugin_name)

    def get_intro_text(self):
        return _('\nType the number of a vmlinux image for more details '
                 'or \'e\' to return to the previous menu.')

    def get_prompt_text(self):
        return _('Select an image: ')

    def get_sub_menu_options(self):
        return self._submenu_opts

    def postinit(self):
        self._submenu_opts = deque()
        kernelext_dir = confighelper.get_config_helper().get(
                                            option='kern_debug_dir')

        image_list = list_extracted_vmlinuxes(kernelext_dir)

        if len(image_list) == 0:
            msg = _('No vmlinux images were found in %s' % (kernelext_dir))
            print msg
            raise Exception(msg)

        for pkg in image_list:
            self._submenu_opts.append(DisplayOption(pkg, 'interactive_action'))

    def non_interactive_action(self):
        for image in self._submenu_opts:
            try:
                print image.display_text.encode("UTF-8", 'replace')
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
                print image.display_text.encode(sys.getdefaultencoding(),
                                   'replace')

    def interactive_action(self, display_option=None):
        pkgname = display_option.display_text
        kernelext_dir = confighelper.get_config_helper().get(
                                            option='kern_debug_dir')
        doc = u''

        if pkgname:
            vmlinuxpath = os.path.join(kernelext_dir, pkgname, 'vmlinux')
            if os.path.exists(vmlinuxpath):
                vmlinux = VMLinux(vmlinuxpath)
                doc += _('Information for %s\n' % (pkgname))
                doc += _(' uname -r string: %s\n' % (vmlinux.get_version()))
                doc += _(' Location: %s\n' % (vmlinuxpath))
                doc += _(' Size: %d bytes' % (os.stat(vmlinuxpath).st_size))
                try:
                    print doc.encode("UTF-8", 'replace')
                # pylint: disable=W0703
                except Exception, e:
                    logger.log(logging.WARNING, e)
                    import sys
                    print doc.encode(sys.getdefaultencoding(),
                                     'replace')
            else:
                raise Exception()
        else:
            raise Exception()
