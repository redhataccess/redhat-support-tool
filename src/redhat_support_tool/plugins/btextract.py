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
from redhat_support_tool.helpers.confighelper import _
from redhat_support_tool.helpers.constants import Constants
from redhat_support_tool.helpers.launchhelper import LaunchHelper
from redhat_support_tool.helpers.vmcorehelper import VMCore
from redhat_support_tool.plugins import InteractivePlugin, DisplayOption, \
                                        ObjectDisplayOption
from redhat_support_tool.plugins.add_attachment import AddAttachment
from redhat_support_tool.plugins.add_comment import AddComment
from redhat_support_tool.plugins.get_kerneldebug import GetKernelDebugPackages
from redhat_support_tool.plugins.diagnose import Diagnose
from redhat_support_tool.plugins.open_case import OpenCase
import logging
import os.path
import pydoc
import redhat_support_tool.helpers.common as common
import redhat_support_tool.helpers.apihelper as apihelper
import redhat_support_tool.helpers.vmcorehelper as vmcorehelper
import redhat_support_tool.helpers.confighelper as confighelper
# pylint: disable=W0402
import string
import subprocess
import tempfile

__author__ = 'Keith Robertson <kroberts@redhat.com>'
logger = logging.getLogger("redhat_support_tool.plugins.btextract")


class BTExtract(InteractivePlugin):
    plugin_name = 'btextract'
    _submenu_opts = None
    _sections = None
    end_of_entries = ''
    vmcore = None
    mkdumpfilepath = None
    # Should interactive_plugin/non_interactive_plugin skip output methods?
    no_submenu = False

    @classmethod
    def get_usage(cls):
        '''
        The usage statement that will be printed by OptionParser.

        Example:
            - %prog -c CASENUMBER [options] <comment text here>
        Important: %prog is a OptionParser built-in.  Use it!
        '''
        return _('%prog [options] </path/to/vmcore>')

    @classmethod
    def get_desc(cls):
        '''
        The description statement that will be printed by OptionParser.

        Example:
            - 'Use the \'%s\' command to add a comment to a case.'\
             % cls.plugin_name
        '''
        return _('Use the \'%s\' command get a kernel stack backtrace and '
                 'other related information from a kernel core dump file. '
                 'The default behavior is to issue \'bt -a\'; however, there '
                 'are a variety of other \'crash\' '
                 'commands that can be run.') % cls.plugin_name

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
  - %s /var/crash/vmcore""") \
  % (cls.plugin_name)

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
        return [Option('-c', '--case', dest='casenumber',
                        help=_('Add the collected data as a comment to the '
                               'provided case.'),
                        default=None),
                Option("-a", "--all", dest="all",
                    action="store_true",
                    help=_('Run all options. Equals -aeflpFi'),
                    default=False),
                Option("-e", "--exframe", dest="exframe",
                    action="store_true",
                    help=_('Search the stack for possible kernel and user '
                           'mode exception frames (ie. bt -e).'),
                    default=False),
                Option("-f", "--foreachbt", dest="foreachbt",
                    action="store_true",
                    help=_('Display the stack traces for all tasks '
                           '(ie. foreach bt).'),
                    default=False),
                Option("-l", "--log", dest="log",
                    action="store_true",
                    help=_('Dumps the kernel log_buf contents in '
                           'chronological order.'),
                    default=False),
                Option("-p", "--ps", dest="ps",
                    action="store_true",
                    help=_('Displays process status for selected processes '
                           'in the system.'),
                    default=False),
                Option("-F", "--files", dest="files",
                    action="store_true",
                    help=_('Displays information about open files.'),
                    default=False),
                Option("-i", "--cmdfile", dest="cmdfile",
                    help=_('Run a sequence of individual \'crash\' commands '
                           'from a file.'),
                    default=None)]

    def get_intro_text(self):
        return _('\nSelect the crash command output to view or \'e\' '
                 'to return to the previous menu.')

    def get_sub_menu_options(self):
        return self._submenu_opts

    def _check_vmcore(self, filename):
        '''
        Will create a VMCore object from a given core file
        or throw an exception if crash has a problem inspecting the
        core file for OSRELEASE.
        '''
        self.vmcore = VMCore(filename)

    def _find_debug_symbols(self):
        '''
        At this point self.vmcore had better be non-null.  This
        method will call vmcorehelper's get_debug_symbols which scans
        the designated debug symbols directory looking for debug symbols
        which match the given core file.  If symbols are found, the
        VMCore object will be passed a VMLinux object.
        '''
        kernelext_dir = confighelper.get_config_helper().get(
                                            option='kern_debug_dir')
        vmlinux = vmcorehelper.get_debug_symbols(
                                kernelext_dir, self.vmcore.getKernelVersion())
        if vmlinux:
            self.vmcore.setDebugSymbols(vmlinux)
        else:
            print _('WARNING: Debug symbols for %s were not found.') % \
                    self._args[0]
            line = raw_input(_('Would you like to install kernel-debuginfo-%s '
                    'from available debug repositories (y/n)? ') % \
                    self.vmcore.getKernelVersion())
            if str(line).strip().lower() == 'y':
                print _('Installing kernel-debuginfo-%s') % \
                    self.vmcore.getKernelVersion()
                lh = LaunchHelper(GetKernelDebugPackages)
                lh.run(self.vmcore.getKernelVersion(),
                       pt_exception=True)
                vmlinux = vmcorehelper.get_debug_symbols(
                                kernelext_dir, self.vmcore.getKernelVersion())
                if vmlinux:
                    self.vmcore.setDebugSymbols(vmlinux)
                else:
                    raise Exception(_('Installation of debug images failed, '
                                      'cannot proceed with debug session'))
            else:
                raise Exception('User elected not to install debug '
                                'packages for kernel-debuginfo-%s' % \
                                self.vmcore.getKernelVersion())

    def validate_args(self):
        if not self._args:
            msg = _('ERROR: %s requires the full path to a kernel core dump '
                    'file.') % self.plugin_name
            print msg
            raise Exception(msg)
        self._check_vmcore(self._args[0])
        try:
            self._find_debug_symbols()
        except Exception, e:
            logger.log(logging.DEBUG, e)
            if os.path.exists('/usr/sbin/makedumpfile'):
                self.mkdumpfilepath = '/usr/sbin/makedumpfile'
            elif os.path.exists('/sbin/makedumpfile'):
                self.mkdumpfilepath = '/sbin/makedumpfile'
            else:
                raise

    def postinit(self):
        self._submenu_opts = deque()
        self._sections = {}

        # If we had to fallback on makedumpfile, lets run it.
        if self.mkdumpfilepath:
            self._mkdumpfile_log_fallback()
        else:
            try:
                self._execute_bt_commands()
            except Exception, e:
                msg = _('ERROR: %s') % e
                print msg
                logger.log(logging.ERROR, msg)
                raise e

        try:
            if self._options['casenumber']:
                # pylint: disable=W0141
                for opt in self._submenu_opts:
                    # Remove nonprintable characters from the
                    # crash output.  Argh!!!!
                    filtered_string = filter(lambda x: x in string.printable,
                                             self._sections[opt])
                    filtered_string = str(filtered_string).replace('"', ' ')
                    filtered_string = str(filtered_string).replace("'", ' ')
                    msg = None

                    # If the filtered_string is too long (comments can only be
                    # ~30k when formatting is applied, plus 20k is a large
                    # chunk of text) attach it instead.
                    if len(filtered_string) > 20000:
                        try:
                            # Because we can't rename on the fly attachments,
                            # this filename is going to look 'odd'.
                            fd, temppath = tempfile.mkstemp(
                                                        prefix="vmcoreinfo-",
                                                        suffix="-rhst")
                            attachment = os.fdopen(fd, "w")
                            attachment.write(filtered_string)
                            attachment.close()
                            lh = LaunchHelper(AddAttachment)
                            lh.run('-c %s --description="%s" %s' % (
                                                self._options['casenumber'],
                                                opt.display_text.encode(
                                                        "UTF-8", 'replace'),
                                                temppath))

                            os.remove(temppath)
                            msg = 'The attachment %s was uploaded by Red Hat' \
                                  ' Support Tool from the VMCore %s' % \
                                  (os.path.basename(temppath),
                                   self.vmcore.coreFilename)
                        except:
                            print _('Unable to upload output to Red Hat'
                                    ' Customer Portal, reverting to displaying'
                                    ' output to console.')
                    else:
                        msg = '%s\nThe following comment was added by ' \
                              'Red Hat Support Tool\nVersion: %s\n' \
                              '%s\n\n%s' % \
                              (str(self.ruler * Constants.MAX_RULE),
                               apihelper.USER_AGENT,
                               str(self.ruler * Constants.MAX_RULE),
                               filtered_string)

                    if msg:
                        common.set_interactive(True)
                        lh = LaunchHelper(AddComment)
                        lh.run('-c %s "%s"' % (self._options['casenumber'],
                                               msg))
                        self.no_submenu = True
        except Exception, e:
            msg = _('ERROR: %s') % e
            print msg
            logger.log(logging.ERROR, msg)
            raise e

    def non_interactive_action(self):
        if self.no_submenu:
            return

        doc = u''
        for opt in self._submenu_opts:
            doc += self._sections[opt]
        try:
            print doc.encode("UTF-8", 'replace')
        # pylint: disable=W0703
        except Exception, e:
            # There are some truly bizarre errors when you pipe
            # the output from python's 'print' function with sys encoding
            # set to ascii. These errors seem to manifest when you pipe
            # to something like 'more' or 'less'.  You'll get encoding errors.
            # Curiously, you don't see them with 'grep' or even simply piping
            # to terminal.  WTF :(
            logger.log(logging.WARNING, e)
            import sys
            print doc.encode(sys.getdefaultencoding(),
                             'replace')

    def interactive_action(self, display_option=None):
        doc = self._sections[display_option]
        pydoc.pipepager(doc.encode("UTF-8", 'replace'), cmd='less -R')

    def _mkdumpfile_log_fallback(self):
        try:
            tempdir = tempfile.mkdtemp('-rhst')
            mkdumpcmd = [self.mkdumpfilepath, "--dump-dmesg",
                         self.vmcore.coreFilename, os.path.join(tempdir,
                                                                'dmesglog')]
            ret = subprocess.call(mkdumpcmd,
                                  stderr=subprocess.STDOUT,
                                  stdout=subprocess.PIPE)
            if ret != 0:
                msg = _("Unable to get core dmesg log using alternate method.")
                raise Exception(msg)

            output = open(os.path.join(tempdir, 'dmesglog')).read()
            disp_opt = DisplayOption(_('Kernel log buffer (dmesg) logs'),
                                     'interactive_action')
            self._submenu_opts.append(disp_opt)
            self._sections[disp_opt] = output

            # Open a support case
            disp_opt = ObjectDisplayOption(
                                _('Open a support case with dmesg logs'),
                                '_opencase',
                                output)
            self._submenu_opts.append(disp_opt)
            self._sections[disp_opt] = output
        except:
            raise

    def _send_to_shadowman(self, display_option=None):
        lh = LaunchHelper(Diagnose)
        lh.run('', display_option)

    def _opencase(self, display_option=None):
        lh = LaunchHelper(OpenCase)
        try:
            # Remove nonprintable characters from the
            # crash output.  Argh!!!!
            filtered_string = filter(lambda x: x in string.printable,
                                     display_option.stored_obj)
            filtered_string = str(filtered_string).replace('"', ' ')
            filtered_string = str(filtered_string).replace("'", ' ')
            msg = None

            # If the filtered_string is too long (comments can only be
            # ~30k when formatting is applied, plus 20k is a large
            # chunk of text) attach it instead.
            if len(filtered_string) > 20000:
                try:
                    # Because we can't rename on the fly attachments,
                    # this filename is going to look 'odd'.
                    fd, temppath = tempfile.mkstemp(
                                                prefix="vmcoreinfo-",
                                                suffix="-rhst")
                    attachment = os.fdopen(fd, "w")
                    attachment.write(filtered_string)
                    attachment.close()
                    lh.run('--attachment=%s' % (temppath))
                    os.remove(temppath)
                except:
                    print _('Unable to upload output to Red Hat'
                            ' Customer Portal, reverting to displaying'
                            ' output to console.')
            else:
                msg = '%s\nThe following comment was added by ' \
                      'Red Hat Support Tool\nVersion: %s\n' \
                      '%s\n\n%s' % \
                      (str(self.ruler * Constants.MAX_RULE),
                       apihelper.USER_AGENT,
                       str(self.ruler * Constants.MAX_RULE),
                       filtered_string)
                lh.run('-d \'%s\'' % msg)

        except Exception, e:
            msg = _('ERROR: %s') % e
            print msg
            logger.log(logging.ERROR, msg)

    def _execute_bt_commands(self):
        '''
        A utility method which executes the BT commands specified by the
        user.
        '''
        if self._options['all']:
            self._options['exframe'] = True
            self._options['foreachbt'] = True
            self._options['log'] = True
            self._options['ps'] = True
            self._options['files'] = True

        # Always do 'bt -a'
        output = self.vmcore.exe_crash_commands('bt -a')
        disp_opt = DisplayOption(_('Output from crash \'bt -a\''),
                                 'interactive_action')
        self._submenu_opts.append(disp_opt)
        self._sections[disp_opt] = output

        if common.is_interactive():
            # Send to Shadowman
            disp_opt = ObjectDisplayOption(_("Diagnose 'bt -a' output"),
                                           '_send_to_shadowman',
                                           output)
            self._submenu_opts.append(disp_opt)
            self._sections[disp_opt] = output

            # Open a support case
            disp_opt = ObjectDisplayOption(
                                _("Open a support case with 'bt -a' output"),
                                '_opencase',
                                output)
            self._submenu_opts.append(disp_opt)
            self._sections[disp_opt] = output

        if self._options['exframe']:
            output = self.vmcore.exe_crash_commands('bt -e')
            disp_opt = DisplayOption(_('Output from crash \'bt -e\''),
                                     'interactive_action')
            self._submenu_opts.append(disp_opt)
            self._sections[disp_opt] = output

        if self._options['foreachbt']:
            output = self.vmcore.exe_crash_commands('foreach bt')
            disp_opt = DisplayOption(_('Output from crash \'foreach bt\''),
                                     'interactive_action')
            self._submenu_opts.append(disp_opt)
            self._sections[disp_opt] = output

        if self._options['log']:
            output = self.vmcore.exe_crash_commands('log')
            disp_opt = DisplayOption(_('Output from crash \'log\''),
                                     'interactive_action')
            self._submenu_opts.append(disp_opt)
            self._sections[disp_opt] = output

        if self._options['ps']:
            output = self.vmcore.exe_crash_commands('ps')
            disp_opt = DisplayOption(_('Output from crash \'ps\''),
                                     'interactive_action')
            self._submenu_opts.append(disp_opt)
            self._sections[disp_opt] = output

        if self._options['files']:
            output = self.vmcore.exe_crash_commands('files')
            disp_opt = DisplayOption(_('Output from crash \'files\''),
                                     'interactive_action')
            self._submenu_opts.append(disp_opt)
            self._sections[disp_opt] = output

        if self._options['cmdfile']:
            try:
                file_contents = open(self._options['cmdfile'], 'r').read()
                output = self.vmcore.exe_crash_commands(file_contents)
                disp_opt = DisplayOption(_('Output from crash -i %s') % \
                                         self._options['files'],
                                         'interactive_action')
                self._submenu_opts.append(disp_opt)
                self._sections[disp_opt] = output
            except Exception, e:
                msg = _('Problem opening %s. Error is: %s') % \
                    (self._options['files'], e)
                logger.log(logging.ERROR, msg)
                raise Exception(msg)
