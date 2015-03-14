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
from redhat_support_tool.plugins import Plugin, ObjectDisplayOption
from redhat_support_tool.plugins.add_comment import AddComment
from redhat_support_tool.helpers import apihelper, common, confighelper
from redhat_support_tool.helpers.launchhelper import LaunchHelper
import redhat_support_lib.utils.reporthelper as reporthelper
import redhat_support_lib.utils.confighelper as libconfighelper
import redhat_support_lib.utils.ftphelper as ftphelper
import os
import sys
import shutil
import logging


__author__ = 'Keith Robertson <kroberts@redhat.com>'
__author__ = 'Spenser Shumaker <sshumake@redhat.com>'

logger = logging.getLogger("redhat_support_tool.plugins.add_attachment")
libconfig = libconfighelper.get_config_helper()


class AddAttachment(Plugin):
    plugin_name = 'addattachment'
    comment = None
    attachment = None
    compressed_attachment = None
    upload_file = None
    split_attachment = False
    use_ftp = False
    max_split_size = libconfig.attachment_max_size

    @classmethod
    def get_usage(cls):
        '''
        The usage statement that will be printed by OptionParser.

        Example:
            - %prog -c CASENUMBER [options] <comment text here>
        Important: %prog is a OptionParser built-in.  Use it!
        '''
        return _('%prog -c CASENUMBER [options] /path/to/file')

    @classmethod
    def get_desc(cls):
        '''
        The description statement that will be printed by OptionParser.

        Example:
            - 'Use the \'%s\' command to add a comment to a case.'\
             % cls.plugin_name
        '''
        return _('Use the \'%s\' command to add an attachment to a case.')\
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
        return _('Examples:\n'
                 '- %s -c 12345678 /var/log/messages\n'
                 '- %s -c 12345678 -d \'The log file containing the error\' '
                 '/var/log/messages\n'
                 '- %s -c 12345678') % \
                 (cls.plugin_name, cls.plugin_name, cls.plugin_name)

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
        max_split_size_mb = cls.max_split_size / 1024 / 1024

        errmsg1 = _("ERROR: can't use -s/--split and -x/--no-split options "
                    "together")
        errmsg2 = _("ERROR: -s/--split takes at most one optional argument "
                    "(found %d: %s)")
        errmsg3 = _("ERROR: the optional argument to -s/--split must be an "
                    "integer between 1 and %d (MB)" % max_split_size_mb)

        def check_nosplit_callback(option, opt_str, value, parser):
            '''
            Callback function for -x/--no-split option
            - Report error if the -s/--split option has already been seen
            '''
            if not parser.values.split is None:
                print errmsg1
                raise Exception(errmsg1)
            parser.values.nosplit = True

        def set_split_size_callback(option, opt_str, value, parser):
            '''
            Callback function for -s/--split option
            - Report error if the -x/--no-split option has already been seen
            The -s/--split option can take 0 or 1 arguments
            - With 0 args - use the default max_split_size
            - With 1 arg  - the argument sets the split size
            - With >1 arg - report error
            '''
            if not parser.values.nosplit is None:
                print errmsg1
                raise Exception(errmsg1)

            assert value is None
            value = []

            def floatable(arg):
                try:
                    float(arg)
                    return True
                except ValueError:
                    return False

            for arg in parser.rargs:
                # stop on --foo like options
                if arg[:2] == "--" and len(arg) > 2:
                    break
                # stop on -a, but not on -3 or -3.0
                if arg[:1] == "-" and len(arg) > 1 and not floatable(arg):
                    break
                value.append(arg)

            if len(value) == 0:
                splitsize = max_split_size_mb
            elif len(value) > 1:
                print (errmsg2 % (len(value), ' '.join(value)))
                raise Exception(errmsg2)
            else:
                try:
                    splitsize = int(value[0])
                except ValueError:
                    print errmsg3
                    raise Exception(errmsg3)
                if splitsize > max_split_size_mb or splitsize < 1:
                    print errmsg3
                    raise Exception(errmsg3)

            del parser.rargs[:len(value)]
            parser.values.split = True
            parser.values.splitsize = splitsize * 1024 * 1024

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
                       callback=public_opt_callback),
                Option("-d", "--description", dest="description",
                        help=_("A description for the attachment. The \
Red Hat Support Tool will generate a default description for the attachment \
if none is provided that contains the name of the file and the RPM package to \
which it belongs if available. (optional)"), default=False),
                Option("-x", "--no-split", dest="nosplit", action='callback',
                       callback=check_nosplit_callback,
                       help=_('Do not attempt to split uploaded files, upload '
                              'may fail as a result if an alternative '
                              'destination is not available.')),
                Option("-s", "--split", dest="split", action="callback",
                       callback=set_split_size_callback,
                       help=_("The uploaded attachment file will be \
intentionally split.  An optional size parameter (in MB) can be supplied and \
the attachment will be split into 'size' (MB) chunks.  Default/Maximum chunk \
size: %d (MB)" % max_split_size_mb)),
                Option("-f", "--use-ftp", dest="useftp",
                       action='store_true', default=False,
                       help=_('Upload via FTP to %s instead of the Red Hat '
                              'Customer Portal.' % libconfig.ftp_host)),
                Option("-z", "--no-compress", dest="nocompress",
                       action='store_true', default=False,
                       help=_("If the attachment file is uncompressed, don't "
                              'compress it for upload.'))]

    def _remove_compressed_attachments(self):
        if self.compressed_attachment and \
           os.path.exists(self.compressed_attachment):
            shutil.rmtree(os.path.dirname(self.compressed_attachment))

    def _check_case_number(self):
        errmsg1 = _("ERROR: %s requires a case number." % self.plugin_name)
        errmsg2 = _("ERROR: %s is not a valid case number.")

        if not self._options['casenumber']:
            if common.is_interactive():
                while True:
                    line = raw_input(_("Please provide a case number (or 'q' "
                                       'to exit): '))
                    line = str(line).strip()
                    if not line:
                        print errmsg1
                    elif line == 'q':
                        print
                        self._remove_compressed_attachments()
                        raise Exception()
                    else:
                        try:
                            int(line)
                            self._options['casenumber'] = line
                            break
                        except ValueError:
                            print(errmsg2 % line)
            else:
                print errmsg1
                self._remove_compressed_attachments()
                raise Exception(errmsg1)

    def _check_description(self):
        if self.use_ftp:
            self._options['description'] = None
            return

        if common.is_interactive():
            if not self._options['description']:
                line = raw_input(_('Please provide a description or '
                                   'enter to accept default (or \'q\' '
                                       'to exit): '))
                line = str(line).strip()
                if line == 'q':
                    print
                    self._remove_compressed_attachments()
                    raise Exception()
                if str(line).strip():
                    self._options['description'] = line

        if not self._options['description']:
            description = '[RHST] File %s' % os.path.basename(self.attachment)
            try:
                package = reporthelper.rpm_for_file(self.attachment)
                if package:
                    description += ' from package %s' % package
            except:
                pass

            self._options['description'] = description

    def _check_is_public(self):
        if confighelper.get_config_helper().get(option='ponies') and \
           common.is_interactive():
            if self._options['public'] is None:
                line = raw_input(_('Is this a public attachment ([y]/n)? '))
                if str(line).strip().lower() == 'n':
                    self._options['public'] = False
                else:
                    self._options['public'] = True
        else:
            if self._options['public'] is None:
                self._options['public'] = True

    def _check_file(self):
        msg = _("ERROR: %s requires a path to a file.")\
                    % self.plugin_name
        self.attachment = None
        if self._args:
            self.attachment = self._args[0]
            self.attachment = os.path.expanduser(self.attachment)
            if not os.path.isfile(self.attachment):
                msg = _('ERROR: %s is not a valid file.') % self.attachment
                print msg
                raise Exception(msg)
        elif common.is_interactive():
            while True:
                line = raw_input(_('Please provide the full path to the'
                                   ' file (or \'q\' to exit): '))
                if str(line).strip() == 'q':
                    print
                    raise Exception()
                line = str(line).strip()
                self.attachment = line
                self.attachment = os.path.expanduser(self.attachment)
                if os.path.isfile(self.attachment):
                    break
                else:
                    print _('ERROR: %s is not a valid file.') \
                        % self.attachment
        else:
            print msg
            raise Exception(msg)

        self.upload_file = self.attachment
        self.use_ftp = self._options['useftp']
        if not (self._options['nocompress'] or \
           ftphelper.is_compressed_file(self.attachment)):
            print _("Compressing %s for upload ..." % self.attachment),
            sys.stdout.flush()
            self.compressed_attachment = ftphelper.compress_attachment(
                                                            self.attachment)
            if self.compressed_attachment:
                print _("completed successfully.")
                self.upload_file = self.compressed_attachment

        if self._options['split']:
            self.split_attachment = True
            return

        attachment_size = os.path.getsize(self.upload_file)
        if not self._options['nosplit'] and not self.use_ftp and \
           (attachment_size > self.max_split_size):
            if common.is_interactive():
                line = raw_input(_('%s is too large to upload to the Red Hat '
                                   'Customer Portal, would you like to split '
                                   'the file before uploading ([y]/n)? ') % (
                                   os.path.basename(self.upload_file)))
                if str(line).strip().lower() == 'n':
                    self.use_ftp = True
                    print _('The attachment will be uploaded via FTP to '
                            '%s instead.' % libconfig.ftp_host)
                    return
            elif not self._options['nosplit']:
                self.use_ftp = True
                return

            self.split_attachment = True

    def validate_args(self):
        self._check_file()
        self._check_case_number()
        self._check_description()
        self._check_is_public()

    def non_interactive_action(self):
        api = None
        updatemsg = None
        if self.use_ftp:
            uploadloc = libconfig.ftp_host
        else: 
            uploadloc = "the case"
        caseNumber = self._options['casenumber']
        uploadBaseName = os.path.basename(self.upload_file)
        try:
            try:
                api = apihelper.get_api()

                print _("Uploading %s to %s ..." % (uploadBaseName,
                                                    uploadloc)),
                sys.stdout.flush()
                if self.split_attachment:
                    chunk = {'num': 0, 'names': [], 'size': self._options.get(
                             'splitsize', self.max_split_size)}
                    retVal = api.attachments.add(
                                    caseNumber=caseNumber,
                                    public=self._options['public'],
                                    fileName=self.upload_file,
                                    fileChunk=chunk,
                                    description=self._options['description'],
                                    useFtp=self.use_ftp)
                    if retVal:
                        print _("completed successfully.")
                        updatemsg = _('[RHST] The following split files were '
                                      'uploaded to %s:\n' % uploadloc)
                        for chunk_name in chunk['names']:
                            updatemsg += _('\n    %s' % chunk_name)

                else:
                    retVal = api.attachments.add(
                                    caseNumber=caseNumber,
                                    public=self._options['public'],
                                    fileName=self.upload_file,
                                    description=self._options['description'],
                                    useFtp=self.use_ftp)
                    if retVal:
                        print _("completed successfully.")
                        if self.use_ftp:
                            updatemsg = _('[RHST] The following attachment was'
                                          ' uploaded to %s:\n\n    %s-%s' %
                                          (libconfig.ftp_host, caseNumber,
                                           uploadBaseName))

                if retVal is None:
                    raise Exception()

                if updatemsg:
                    lh = LaunchHelper(AddComment)
                    comment_displayopt = ObjectDisplayOption(None, None,
                                                             [updatemsg])
                    lh.run('-c %s' % caseNumber, comment_displayopt)

            except EmptyValueError, eve:
                msg = _("ERROR: %s") % str(eve)
                print _("failed.\n" + msg)
                logger.error(msg)
                raise
            except RequestError, re:
                msg = _("ERROR: Unable to connect to support services API.  "
                        "Reason: %s    " % re.reason)
                print _("failed.\n" + msg)
                logger.error(msg)
                raise
            except ConnectionError:
                msg = _("ERROR: Problem connecting to the support services "
                        "API.  Is the service accessible from this host?")
                print _("failed.\n" + msg)
                logger.error(msg)
                raise
            except Exception:
                msg = _("ERROR: Problem encountered whilst uploading the "
                        "attachment.  Please consult the Red Hat Support Tool "
                        "logs for details.")
                print _("failed.\n" + msg)
                logger.error(msg)
                raise
        finally:
            self._remove_compressed_attachments()
            print
