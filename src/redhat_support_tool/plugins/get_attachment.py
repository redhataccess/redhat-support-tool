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
from redhat_support_tool.plugins import Plugin
import logging
import os
import redhat_support_tool.helpers.apihelper as apihelper
import redhat_support_tool.helpers.common as common
import re
import sys

__author__ = 'Spenser Shumaker <sshumake@redhat.com>'
logger = logging.getLogger("redhat_support_tool.plugins.get_attachment")


class GetAttachment(Plugin):
    plugin_name = 'getattachment'

    @classmethod
    def get_usage(cls):
        '''
        The usage statement that will be printed by OptionParser.

        Example:
            - %prog -c CASENUMBER [options] <comment text here>
        Important: %prog is a OptionParser built-in.  Use it!
        '''
        return _('%prog -c CASENUMBER -u ATTACHMENTUUID [options]')

    @classmethod
    def get_desc(cls):
        '''
        The description statement that will be printed by OptionParser.

        Example:
            - 'Use the \'%s\' command to add a comment to a case.'\
             % cls.plugin_name
        '''
        return _('Use the \'%s\' command to find a specific attachment '
                 'by number.') % cls.plugin_name

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
- %s -c 12345678 -u AAABBBCCCDDDEEE -d ~/Downloads
- %s -c 12345678 -a -s -m -d ~/Downloads""") % (cls.plugin_name,
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
        return [Option("-c", "--casenumber", dest="casenumber",
                       help=_('The case number from which the attachment '
                       'will be downloaded. (required)'), default=None),
                Option("-u", "--attachmentuuid", dest="attachmentuuid",
                       help=_("UUID of the attachment to be downloaded."),
                       default=None),
                Option("-a", "--all", dest="downloadall",
                       help=_("Download all attachments for this case."),
                       action="store_true", default=False),
                Option("-i", "--include", dest="include",
                       help=_("Limit download all attachments to those"
                              " matching regex."),
                       default=None),
                Option("-x", "--exclude", dest="exclude",
                       help=_("Limit download all attachments to those NOT"
                              " matching regex."),
                       default=None),
                Option("-s", "--sorted", dest="sorted",
                       help=_("Sort attachment filenames according to "
                              "creation date. (only with -a)"),
                       action="store_true",
                       default=False),
                Option("-m", "--metadata", dest="metadata",
                       help=_("Save a XML file with metadata for the given "
                               "attachment. (only with -a)"),
                       action="store_true",
                       default=False),
                Option("-z", "--maxsize", dest="maxsize",
                       help=_("Maximum attachment size to download, in bytes."
                               " (only with -a)"),
                       action="store",
                       type="int",
                       default=0),
                Option("-d", "--destdir", dest="destdir",
                       help=_("Destination directory the attachment will be"
                       " saved."), default=None)]

    def _check_case_number(self):
        msg = _("ERROR: %s requires a case number.")\
                    % self.plugin_name

        if not self._options['casenumber']:
            if common.is_interactive():
                line = raw_input(_('Please provide a case number (or \'q\' '
                                       'to exit): '))
                line = str(line).strip()
                if line == 'q':
                    raise Exception()
                if str(line).strip():
                    self._options['casenumber'] = line
                else:
                    print msg
                    raise Exception(msg)
            else:
                print msg
                raise Exception(msg)

    def _check_destdir(self):
        beenVerified = False
        if not self._options['destdir']:
            if common.is_interactive():
                while True:
                    line = raw_input(_('Please provide a download directory '
                                       'or press enter to use the current '
                                       'directory (or \'q\' to exit): '))
                    if str(line).strip() == 'q':
                        raise Exception()
                    line = str(line).strip()
                    destDir = os.path.expanduser(line)
                    if not len(destDir):
                        destDir = os.curdir
                    if not os.path.isdir(destDir):
                        print(_('%s is not a valid directory.') % destDir)
                    else:
                        self._options['destdir'] = destDir
                        beenVerified = True
                        break
            else:
                self._options['destdir'] = os.curdir

        if not beenVerified:
            self._options['destdir'] = os.path.\
                expanduser(self._options['destdir'])
            if not os.path.isdir(self._options['destdir']):
                msg = _('ERROR: %s is not a valid directory.') \
                    % self._options['destdir']
                print msg
                raise Exception(msg)

    def _check_mode(self):
        if self._options['downloadall']:
            if self._options['attachmentuuid']:
                msg = _('ERROR: -a cannot be used with -u option')
                print msg
                raise Exception(msg)
            # Okay then. Only -a, process -m and -s later.
            return

        if self._options['include']:
            msg = _('ERROR: %s is only effective when using %s') % ('-i', '-a')
            print msg
            raise Exception(msg)
        if self._options['exclude']:
            msg = _('ERROR: %s is only effective when using %s') % ('-x', '-a')
            print msg
            raise Exception(msg)

        if not self._options['attachmentuuid']:
            msg = _('ERROR: %s requires the UUID of the attachment to be '
                    'downloaded.') % self.plugin_name
            if common.is_interactive():
                line = raw_input(_('Please provide the UUID '
                                   'of an attachment(\'q\' '
                                       'to exit): '))
                line = str(line).strip()
                if line == 'q':
                    raise Exception()
                if str(line).strip():
                    self._options['attachmentuuid'] = line
                else:
                    print msg
                    raise Exception(msg)
            else:
                print msg
                raise Exception(msg)

        # As user supplied -u, we can't use -s, -m or -z here.
        for value, opt in {'sorted': '-s', 'metadata': '-m', 'maxsize': '-z'}.items():
            if self._options[value]:
                msg = _('ERROR: %s is only supported when using -a') % opt
                print msg
                raise Exception(msg)

    def validate_args(self):
        self._check_case_number()
        self._check_mode()
        self._check_destdir()

    def non_interactive_action(self):
        if self._options['downloadall']:
            self._downloadall()
            return

        self.downloaduuid(self._options['attachmentuuid'])

    def _downloadall(self):
        attachs = self._listattachs()
        attachs.sort(key=lambda x: x.get_createdDate())
        attachs.reverse()
        count = 10 * (len(attachs) + 1)
        include = None
        if self._options['include']:
            include = re.compile(self._options['include'])
        exclude = None
        if self._options['exclude']:
            exclude = re.compile(self._options['exclude'])

        for attach in attachs:
            if not attach.get_active() or attach.get_deprecated():
                continue

            count -= 10
            fileName = attach.get_fileName()
            attachmentLength = attach.get_length()

            if include and not include.match(fileName):
                print _('Skipping %s (does not match include regex)') % fileName
                continue
            if exclude and exclude.match(fileName):
                print _('Skipping %s (matches exclude regex)') % fileName
                continue
            if self._options['maxsize'] and \
				self._options['maxsize'] < attachmentLength:
                print _('Skipping %s (%d bytes exceeds size limit)') % \
                    (fileName, attachmentLength)
                continue

            if self._options["sorted"]:
                fileName = '%d-%s' % (count, fileName)

            try:
                s = os.stat(fileName)
                if s.st_size == attachmentLength:
                    # Download exists and finished
                    continue
                # Partial download, cleanup
                os.unlink(fileName)
            except OSError:
                pass

            print _('Downloading %s...') % fileName

            if self._options["metadata"]:
                fmeta = '%d-%s.xml' % (count + 1, attach.get_fileName())
                fmeta = os.path.join(self._options['destdir'], fmeta)
                fp = open(fmeta, 'w')
                fp.write(attach.toXml())
                fp.close()

            self.downloaduuid(attach.get_uuid(), fileName, attachmentLength)

    def _listattachs(self):
        api = None
        try:
            api = apihelper.get_api()
            return api.attachments.list(self._options['casenumber'])
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

    def downloaduuid(self, uuid, filename=None, length=None):
        api = None
        try:
            api = apihelper.get_api()
            if not length:
                logger.debug("Getting attachment length ...")
                print _("Downloading ... "),
                sys.stdout.flush()
                all_attachments = api.attachments.list(self._options['casenumber'])
                for attach in all_attachments:
                    if attach.get_uuid() == uuid:
                        length = attach.get_length()
                        logger.debug("... %d bytes" % length)
                        break
            filename = api.attachments.get(
                                caseNumber=self._options['casenumber'],
                                attachmentUUID=uuid,
                                fileName=filename,
                                attachmentLength=length,
                                destDir=self._options['destdir'])
            print _('File downloaded to %s') % (filename)
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
            msg = _("Unable to get attachment")
            print msg
            logger.log(logging.WARNING, msg)
            raise
