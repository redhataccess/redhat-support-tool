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
from redhat_support_tool.helpers.confighelper import _
import redhat_support_tool.helpers.analyzer as analyzer
import fnmatch
import logging
import os
import rpm
import struct
import subprocess
import tempfile

__author__ = 'Rex White <rexwhite@redhat.com>'
__author__ = 'Keith Robertson <kroberts@redhat.com>'
logger = logging.getLogger("redhat_support_tool.helpers.vmcorehelper")


class VMLinux(object):
    '''
    The VMLinux class represents a vmlinux file and is primarily intended
    for use as a means to extract the kernel version from a vmlinux kernel
    debug symbol file.
    '''
    version = None
    filename = None

    class ELFHeader(object):

        def __init__(self, vmlinux_file):
            '''
            Constructor for ELFHeader.  Takes a file object for the vmlinux
            file as an argument
            '''
            # read the ELF header from the vmlinux file...
            # verify ELF "magic number" file signature
            self.elfHdr_magic = vmlinux_file.read(4)
            if self.elfHdr_magic != "\x7fELF":
                # ELF "magic number" file signature invalid: not a valid ELF
                # file
                msg = _('ERROR: %s is an invalid ELF file!.')
                print msg
                logger.log(logging.ERROR, msg)
                raise Exception(msg)

            # read rest of ELF identification stuff...

            self.elfHdr_class = vmlinux_file.read(1)

            # determine "endian-ness" of file and set up converters
            self.elfHdr_encoding = vmlinux_file.read(1)
            if self.elfHdr_encoding == '\x01':
                # little endian...
                self.endianness = '<'
            elif self.elfHdr_encoding == '\x02':
                # big endian...
                self.endianness = '>'
            else:
                msg = _('ERROR: %s has an unrecognized byte encoding.')
                print msg
                logger.log(logging.ERROR, msg)
                raise Exception(msg)

#            VMLinux.Elf64_Half = struct.Struct(endianness + 'H')
#            VMLinux.Elf64_Word = struct.Struct(endianness + 'I')
#            VMLinux.Elf64_Long = struct.Struct(endianness + 'Q')

            self.elfHdr_version = vmlinux_file.read(1)
            self.elfHdr_OSABI = vmlinux_file.read(1)
            self.elfHdr_ABIVersion = vmlinux_file.read(1)
            self.elfHdr_padding = vmlinux_file.read(7)

            # read rest of ELF header...
            self.elfHdr_ObjType = \
                struct.unpack(self.endianness + 'H',
                                          vmlinux_file.read(2))[0]
            self.elfHdr_MachineType = \
                struct.unpack(self.endianness + 'H',
                                          vmlinux_file.read(2))[0]
            self.elfHdr_version = \
                struct.unpack(self.endianness + 'I',
                                          vmlinux_file.read(4))[0]
            self.elfHdr_entry = \
                struct.unpack(self.endianness + 'Q', vmlinux_file.read(8))[0]
            self.elfHdr_ProgHdrOff = \
                struct.unpack(self.endianness + 'Q', vmlinux_file.read(8))[0]
            self.elfHdr_SectHdrOff = \
                struct.unpack(self.endianness + 'Q', vmlinux_file.read(8))[0]
            self.elfHdr_flags = \
                struct.unpack(self.endianness + 'I',
                                          vmlinux_file.read(4))[0]
            self.elfHdr_HdrSize = \
                struct.unpack(self.endianness + 'H',
                                          vmlinux_file.read(2))[0]
            self.elfHdr_ProgHdrEntSize = \
                struct.unpack(self.endianness + 'H',
                                          vmlinux_file.read(2))[0]
            self.elfHdr_ProgHdrEntCount = \
                struct.unpack(self.endianness + 'H',
                                          vmlinux_file.read(2))[0]
            self.elfHdr_SectHdrEntSize = \
                struct.unpack(self.endianness + 'H',
                                          vmlinux_file.read(2))[0]
            self.elfHdr_SectHdrEntCount = \
                struct.unpack(self.endianness + 'H',
                                          vmlinux_file.read(2))[0]
            self.elfHdr_SectNameStrTableIdx = \
                struct.unpack(self.endianness + 'H',
                                          vmlinux_file.read(2))[0]

        def __str__(self):
            result = "encoding:" + repr(self.elfHdr_encoding)
            result += "\nObject type: " + str(self.elfHdr_ObjType)
            result += "\nMachine type: " + str(self.elfHdr_MachineType)
            result += "\nVersion: " + str(self.elfHdr_version)
            result += "\nEntry point addr: " + str(self.elfHdr_entry)
            result += "\nProgram header offset: " + str(self.elfHdr_ProgHdrOff)
            result += "\nSection header offset: " + str(self.elfHdr_SectHdrOff)
            result += "\nFlags: " + str(self.elfHdr_flags)
            result += "\nELF header size: " + str(self.elfHdr_HdrSize)
            result += "\nProgram header entry size: " + \
                str(self.elfHdr_ProgHdrEntSize)
            result += "\nProgram header entry count: " + \
                str(self.elfHdr_ProgHdrEntCount)
            result += "\nSection header entry size: " + \
                str(self.elfHdr_SectHdrEntSize)
            result += "\nSection header entry count: " + \
                str(self.elfHdr_SectHdrEntCount)
            result += "\nSection name string table index: " + \
                str(self.elfHdr_SectNameStrTableIdx)

            return result

    class ELFSectionHdr(object):

        def __init__(self, vmlinux_file, elf_hdr):

            # read section table entry from file
            self.sect_name = struct.unpack(elf_hdr.endianness + 'I',
                                                       vmlinux_file.read(4))[0]
            self.sect_type = struct.unpack(elf_hdr.endianness + 'I',
                                                       vmlinux_file.read(4))[0]
            self.sect_flags = \
                struct.unpack(elf_hdr.endianness + 'Q',
                              vmlinux_file.read(8))[0]
            self.sect_address = \
                struct.unpack(elf_hdr.endianness + 'Q',
                              vmlinux_file.read(8))[0]
            self.sect_offset = \
                struct.unpack(elf_hdr.endianness + 'Q',
                              vmlinux_file.read(8))[0]
            self.sect_size = struct.unpack(elf_hdr.endianness + 'Q',
                                           vmlinux_file.read(8))[0]
            self.sect_link = struct.unpack(elf_hdr.endianness + 'I',
                                           vmlinux_file.read(4))[0]
            self.sect_info = struct.unpack(elf_hdr.endianness + 'I',
                                           vmlinux_file.read(4))[0]
            self.sect_align = \
                struct.unpack(elf_hdr.endianness + 'Q',
                              vmlinux_file.read(8))[0]
            self.sect_entrySize = \
                struct.unpack(elf_hdr.endianness + 'Q',
                              vmlinux_file.read(8))[0]

            # skip any leftover stuff at the end of this segment header
            vmlinux_file.seek(elf_hdr.elfHdr_SectHdrEntSize - 64, 1)

        def __str__(self):
            result = "Section name: " + str(self.sect_name)
            result += "\nSection type: " + str(self.sect_type)
            result += "\nSection flags: " + str(self.sect_flags)
            result += "\nSection address: {0:x}".format(self.sect_address)
            result += "\nSection offset: {0:x}".format(self.sect_offset)
            result += "\nSection size: {0:x}".format(self.sect_size)
            result += "\nSection link: " + str(self.sect_link)
            result += "\nSection info: " + str(self.sect_info)
            result += "\nSection aligment: {0:x}".format(self.sect_align)
            result += "\nSection entry size: {0:x}".format(self.sect_entrySize)

            return result

    def __init__(self, filename):
        '''
        Constructor for VMLinux.  Takes the filename of a vmlinux file
        as an argument
        '''
        self.filename = filename

        # open file
        vmlinux = open(filename, 'rb')

        # read ELF header from file
        hdr = self.ELFHeader(vmlinux)
#        logger.log(logging.DEBUG, str(hdr))

        # read ELF section headers
        vmlinux.seek(hdr.elfHdr_SectHdrOff, 0)
        sections = []
        for i in range(hdr.elfHdr_SectHdrEntCount):
            sections.append(self.ELFSectionHdr(vmlinux, hdr))
#            logger.log(logging.DEBUG, str(i))

        # read the section name string table from the indicated section
        string_sect = sections[hdr.elfHdr_SectNameStrTableIdx]
        vmlinux.seek(string_sect.sect_offset, 0)

        # WARNING!!  This can blow up, so do something clever...
        strings = vmlinux.read(string_sect.sect_size)

        # find the offset for ".rodata"
        ro_offset = strings.find(".rodata", 1)
        if ro_offset == -1:
            msg = _('ERROR: There is no segment named .rodata in %s') % \
                filename
            print msg
            logger.log(logging.ERROR, msg)
            raise Exception(msg)

        # now find the .rodata section...
#        print "\nSearching for .rodata section..."
        for i in range(len(sections)):
            if sections[i].sect_name == ro_offset:
#                print ".rodata is segment number {0:d}".format(i)

                # now grab the first 192 bytes of the string starting at byte
                # 32 of this section...
                vmlinux.seek(sections[i].sect_offset + 32, 0)
                id_string = vmlinux.read(192).split()

                # validate string
                logger.log(logging.DEBUG,
                           '%s id string is %s' % (filename,
                                                   id_string))
                if id_string[0] == 'Linux':
                    if id_string[1] == 'version':
                        logger.log(logging.DEBUG,
                                   '%s version is %s' % (filename,
                                                         id_string[2]))
                        self.version = str(id_string[2]).strip()

    def get_version(self):
        '''
        A utility function to return the vmlinux version
        '''
        return self.version

    def get_filename(self):
        return self.filename


class VMCore(object):
    '''
    The VMCore class represents a vmcore file, from which we can extract a
    backtrace
    '''
    coreFilename = None
    kernelVersion = None
    vmlinux = None

    def __init__(self, filename):
        '''
        Constructor
        '''
        if not os.access(filename, os.R_OK):
            msg = _('ERROR: unable to read %s') % filename
            print msg
            raise Exception(msg)
        logging.log(logging.DEBUG, 'Analyzing %s', filename)
        # Check for crash
        ts = rpm.TransactionSet()
        mi = ts.dbMatch('provides', 'crash')
        if mi is None or mi.count() != 1:
            msg = _('ERROR: \'crash\' is not installed. Please install '
                    '\'crash\' as root (ie. yum install crash)')
            print msg
            logging.log(logging.ERROR, msg)
            raise Exception(msg)

        self.coreFilename = filename
        self.kernelVersion = self._getKernelVersion()

    def _getKernelVersion(self):
        '''
        getKernelVersion() extracts and returns the OSRELEASE (kernel version)
        string from the target core file
        '''
        # determine vmcore osrelease
        # get crash to do the heavy lifting for us
        try:
            proc = subprocess.Popen(["crash", "--osrelease", self.coreFilename],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            stdout, stderr = proc.communicate()
            if proc.returncode == 0:
                logger.log(logging.DEBUG,
                           'Detected kernel version of %s is %s' %
                           (self.coreFilename, str(stdout).strip()))
                return  str(stdout).strip()
            else:
                p1 = subprocess.Popen(["strings", self.coreFilename],
                                        stdout=subprocess.PIPE)
                for line in iter(p1.stdout.readline, ''):
                    if 'el' in line:
                        p1.stdout.close()
                        logger.log(logging.DEBUG,
                                   'Detected kernel version of %s is %s' %
                                   (self.coreFilename, str(line).strip()))
                        return  str(line).strip()

                # Not found
                p1.stdout.close()
                msg = _('Unable to determine vmcore kernel version of ' +
                        self.coreFilename + ': ')
                if not stderr:
                    msg += _('%s' % str(stdout).strip())
                else:
                    msg += _('%s' % stderr)
                logger.log(logging.DEBUG, msg)
                raise Exception(msg)
        except Exception, e:
            msg = _('ERROR: Unable to launch crash. Message: %s') % e
            print msg
            logger.log(logging.ERROR, msg)
            raise Exception(msg)

    def getKernelVersion(self):
        '''
        getKernelVersion() extracts and returns the OSRELEASE (kernel version)
        string from the target core file
        '''
        return self.kernelVersion

    def setDebugSymbols(self, vmlinux=None):
        '''
        A setter function for attaching a VMLinux to this VMCore.  A valid
        VMLinux is a pre-requisite to any BT work.
        '''
        self.vmlinux = vmlinux

    def getDebugSymbols(self):
        return self.vmlinux

    def exe_crash_commands(self, commands=None):
        '''
        A utility function which executes a set of crash commands
        on this object.

        Arguments:
            commands: A newline separated sequence of commands
                      to execute.  One command per-line.
                      See the -i option in crash.

        Returns:
            The stdout from crash or None
        '''
        retVal = None
        tf = None
        tempfilename = None

        if not commands:
            logger.log(logging.DEBUG,
                       'commands is None')
            return retVal

        if self.vmlinux:
            try:
                (tf, tempfilename) = tempfile.mkstemp()
                tf = os.fdopen(tf, 'w')
                tf.write(commands)
                tf.write('\nquit')
                tf.close()

                logger.log(logging.DEBUG,
                           'Crash command file is %s with contents of:\n%s' %
                           (tempfilename,
                            open(tempfilename, 'r').read()))
                cmd = ['crash', self.coreFilename, self.vmlinux.get_filename(),
                       '-i', tempfilename]
                logger.log(logging.DEBUG, 'Executing: %s ' % " ".join(cmd))
                proc = subprocess.Popen(cmd,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)

                stdout, stderr = proc.communicate()
                if proc.returncode == 0:
                    logger.log(logging.DEBUG,
                               'Crash output %s' % str(stdout).strip())
                    retVal = str(stdout).strip().replace('\r', '\n')
                    if commands == 'bt -a':
                        clean = analyzer.Analyzer.analyze(
                                        retVal, ["Crash bt -a Analyzer", ])
                        retVal = clean[0].token_string
                else:
                    msg = _('ERROR: Problem executing crash command: %s' %
                            stderr)
                    if not stderr:
                        logger.error('%s\nCommand: %s\nOutput:\n%s' %
                                     (msg, ' '.join(cmd), str(stdout).strip()))
                        msg += _('\nPlease consult the Red Hat Support Tool '
                                 'logs for more details.')
                    print msg
                    raise Exception(msg)

                # Cleanup
                if tf:
                    os.unlink(tempfilename)
            except Exception, e:
                if tf:
                    os.unlink(tempfilename)
        else:
            logger.log(logging.DEBUG,
                       'There is no vmlinux objec associated with %s' %
                       self.coreFilename)
            return retVal
        return retVal


def get_debug_symbols(kernelext_dir, kernel_version=None):
    '''
    A utility function that will search the configured
    debug symbol cache directory.  For vmlinux files matching
    the provided kernel version.  This must be version from
    /proc/version (ie. 3.6.11-1.fc17.x86_64)

    Returns:
        A VMLinux object or None

    '''
    retVal = None

    logger.log(logging.DEBUG, 'Searching %s for debug symbols '
               'matching %s' % (kernelext_dir, kernel_version))

    for root, dirnames, filenames in \
        os.walk(kernelext_dir):
        for filename in fnmatch.filter(filenames, '*vmlinux*'):
            logger.log(logging.DEBUG, 'Inspecting %s' % filename)
            vm = VMLinux(os.path.join(root, filename))
            if vm.get_version() == kernel_version:
                logger.log(logging.DEBUG,
                           '%s is a match for %s' %
                           (os.path.join(root, filename), kernel_version))
                retVal = vm
    return retVal


def list_extracted_vmlinuxes(kernelext_dir):
    debugimages = []

    if os.path.exists(kernelext_dir):
        debugdirs = os.listdir(kernelext_dir)

        for pkgname in debugdirs:
            if os.path.exists(os.path.join(kernelext_dir, pkgname, 'vmlinux')):
                debugimages.append(pkgname)

    return debugimages


if __name__ == "__main__":
    # enable verbose logging
    logging.basicConfig(level=logging.DEBUG)
    # create core object from vmcore file
    core = VMCore("/home/keith/bt/cores/vmcore")
    vm = get_debug_symbols(core.getKernelVersion())
    core.setDebugSymbols(vm)
    # extract backraceexecute_crash_commandsecute_crash_commands()
