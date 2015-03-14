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
from redhat_support_tool.helpers.confighelper import EmptyValueError, _
from redhat_support_tool.plugins import InteractivePlugin, ObjectDisplayOption
from redhat_support_tool.helpers import common
from redhat_support_tool.helpers.launchhelper import LaunchHelper
from redhat_support_tool.helpers.yumdownloadhelper import YumDownloadHelper, \
                                                          NoReposError
from redhat_support_tool.plugins.get_kerneldebug import GetKernelDebugPackages
import logging
import os


__author__ = 'Nigel Jones <nigjones@redhat.com>'
__author__ = 'Keith Robertson <kroberts@redhat.com>'
logger = logging.getLogger("redhat_support_tool.plugins.listkerneldebugs")


class ListKernelDebugs(InteractivePlugin):
    plugin_name = 'findkerneldebugs'
    pkgAry = None
    _submenu_opts = None
    _sections = None
    yumhelper = None
    yumquery = None

    @classmethod
    def get_usage(cls):
        '''
        The usage statement that will be printed by OptionParser.

        Example:
            - %prog -c CASENUMBER [options] <comment text here>
        Important: %prog is a OptionParser built-in.  Use it!
        '''
        return _('%prog <package name>')

    @classmethod
    def get_desc(cls):
        '''
        The description statement that will be printed by OptionParser.

        Example:
            - 'Use the \'%s\' command to add a comment to a case.'\
             % cls.plugin_name
        '''
        return _('Use the \'%s\' command to search and install available '
                 'debug images.  Wildcards are allowed.  (requires root user '
                 'privileges)') % cls.plugin_name

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
  - %s 2.6.32-343.el6
  - %s 2.6.18-128.*
  - %s -t xen 2.6.18-348.el5""") \
  % (cls.plugin_name, cls.plugin_name, cls.plugin_name)

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
        return [Option("-t", "--variant", dest="variant",
                       help=_('Select an alternative kernel variant'),
                       metavar=_('VARIANT'))]

    def validate_args(self):
        msg = _('ERROR: %s requires a package name.') % \
                ListKernelDebugs.plugin_name

        if not self._line:
            if common.is_interactive():
                line = raw_input(_('Please provide the text to search (or'
                                   ' \'q\' to exit): '))
                line = str(line).strip()
                if line == 'q':
                    raise Exception()
                if str(line).strip():
                    self._line = line
            else:
                print msg
                raise Exception(msg)

        if len(self._args) == 0 and len(self._line) > 0:
            self._args = [self._line]

        if self._options['variant']:
            self.yumquery = 'kernel-%s-debuginfo-%s' % \
                (self._options['variant'], self._args[0])
        else:
            self.yumquery = 'kernel-debuginfo-%s' % (self._args[0])

    def get_intro_text(self):
        return _('\nType the number of the kernel debug package to install or '
                 '\'e\' to return to the previous menu.')

    def get_prompt_text(self):
        return _('Select a Debug Package: ')

    def get_sub_menu_options(self):
        return self._submenu_opts

    def postinit(self):
        self._submenu_opts = deque()
        self._sections = {}

        try:
            if os.geteuid() != 0:
                raise Exception(_('This command requires root user '
                                  'privileges.'))
            self.yumhelper = YumDownloadHelper()
            self.yumhelper.setup_debug_repos()
            self.pkgAry = self.yumhelper.find_package(self.yumquery)
            if not self.pkgAry:
                raise EmptyValueError(
                        _('%s was not available from any of the following'
                          ' yum repositories: %s') % (self.yumquery,
                                    ', '.join(self.yumhelper.get_repoids())))

            for pkg in self.pkgAry:
                if hasattr(pkg, 'evr'):
                    pkgevr = pkg.evr
                else:
                    pkgevr = "%s:%s-%s" % (pkg.epoch, pkg.version, pkg.release)
                doc = u''
                doc += '%-40s %-20s %-16s' % (pkg.name, pkgevr, pkg.repoid)
                disp_opt_doc = u'%s-%s (%s)' % (pkg.name, pkgevr, pkg.repoid)
                packed_pkg = {'yumhelper': self.yumhelper,
                              'package': pkg}
                disp_opt = ObjectDisplayOption(disp_opt_doc,
                                               'interactive_action',
                                               packed_pkg)
                self._submenu_opts.append(disp_opt)
                self._sections[disp_opt] = doc
        except NoReposError, nre:
            print nre
            raise
        except EmptyValueError, eve:
            print eve
            raise
        except Exception, e:
            msg = _("ERROR: Unable to get debug packages.  %s") % e
            print msg
            logger.log(logging.ERROR, msg)
            raise

    def non_interactive_action(self):
        doc = u''
        doc += '%-40s %-20s %-16s\n' % ("Name", "Version", "Repository")

        for opt in self._submenu_opts:
            doc += self._sections[opt]
            try:
                print doc.encode("UTF-8", 'replace')
            # pylint: disable=W0703
            except Exception, e:
                # There are some truly bizarre errors when you pipe
                # the output from python's 'print' function with sys encoding
                # set to ascii. These errors seem to manifes when you pipe
                # to something like 'more' or 'less'.  You'll get encoding
                # errors. Curiously, you don't see them with 'grep' or
                # even simply piping to terminal.  WTF :(
                logger.log(logging.WARNING, e)
                import sys
                print doc.encode(sys.getdefaultencoding(),
                                 'replace')
            doc = u''

    def interactive_action(self, display_option=None):
        if display_option:
            lh = LaunchHelper(GetKernelDebugPackages)
            lh.run('', display_option)
        else:
            raise Exception()
