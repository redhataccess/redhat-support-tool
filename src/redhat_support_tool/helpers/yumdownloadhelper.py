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

'''
A module that facilitates access to the Yum API.
'''
from redhat_support_tool.helpers.confighelper import _
from urlgrabber.progress import TextMeter
from yum.rpmtrans import RPMBaseCallback
import fnmatch
import logging
import os
import redhat_support_tool.helpers.confighelper as confighelper
import shutil
import subprocess
import sys
import tempfile
import yum

__author__ = 'Nigel Jones <nigjones@redhat.com>'
__author__ = 'Keith Robertson <kroberts@redhat.com>'
logger = logging.getLogger("redhat_support_tool.helpers.yumdownloadhelper")
_yum_helper = None


class NoReposError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)


class NullMeter(RPMBaseCallback):
    def event(self, package, action, te_current,
              te_total, ts_current, ts_total):
        '''
        Without this Yum will send annoying installation progress to stdout.
        '''
        pass


class YumDownloadHelper(yum.YumBase):
    def __init__(self):
        '''
        Returns an initialized yum.YumBase object.

        Important:
         You must close() the object after performing a transaction.
        '''
        yum.YumBase.__init__(self)
        # You must do this so that Yum doesn't spam the console.
        self.doConfigSetup(debuglevel=0, errorlevel=0)

        # Initialize Yum.
        if hasattr(yum.YumBase, 'setCacheDir'):
            # Newer version appear to use this
            self.setCacheDir()
            self._override_sigchecks = True
        else:
            # Older use this.
            self._getConfig()
            setattr(self,
                    '_checkSignatures',
                    lambda x, y: True)

        # Set the progress bar
        self.repos.setProgressBar(TextMeter(fo=sys.stdout))

    def setup_repos(self,
                    repos_to_enable=None,
                    repos_to_disable=None):

        if repos_to_disable:
            self.repos.disableRepo(repos_to_disable)
        if repos_to_enable:
            self.repos.enableRepo(repos_to_enable)

        self.repos.setProgressBar(None)
        self.doRepoSetup()

        enabled_repos = self.repos.listEnabled()
        match_count = 0

        for repo in enabled_repos:
            if fnmatch.fnmatch(repo.id, repos_to_enable):
                match_count = match_count + 1

        if len(enabled_repos) == 0 or match_count == 0:
            raise NoReposError(_('No repositories matching %s were able to be'
                                 ' enabled, please ensure that your system is'
                                 ' subscribed to the appropriate software'
                                 ' repositories.' % (repos_to_enable)))

        # Re-enable the file download text meter
        self.repos.setProgressBar(TextMeter(fo=sys.stdout))

    def setup_debug_repos(self,
                          repos_to_enable='*debug*',
                          repos_to_disable='*'):
        debug_repos = confighelper.get_config_helper().get(
                                                       option='debug_repos')
        if debug_repos:
            repos_to_enable = debug_repos

        self.setup_repos(repos_to_enable, repos_to_disable)

    def get_repoids(self):
        '''Return a list of repoids
        Iterates over repos.listEnabled() and assembles a list of the
        repository ids used by yum.
        '''
        repoids = []
        for repo in self.repos.listEnabled():
            repoids.append(repo.id)
        return repoids

    def find_package(self, query=None):
        '''
        Find package in the available repos. WARNING: by default this
        function only searches the debug repos.  You need to change
        the args to search other repos.

        Keyword arguments:
         query            -- A package name.  Wildcards allowed.

        Returns:
             An array yum package objects.
        '''
        retVal = None
        try:
            self.repos.setProgressBar(None)
            retVal = self.pkgSack.returnPackages(patterns=[query])
            # Re-enable the file download text meter
            self.repos.setProgressBar(TextMeter(fo=sys.stdout))
        except Exception, e:
            logger.log(logging.ERROR, e)
            logger.exception(e)
        return retVal

    def isSpaceToDownloadPackage(self, pkgobj):
        if not os.path.exists(pkgobj.localPkg()):
            fs_stat = os.statvfs(os.path.dirname(pkgobj.localPkg()))
            fs_size = (fs_stat.f_bavail * fs_stat.f_frsize)
            if pkgobj.size > fs_size:
                msg = _("Package size: %d MB > Available space: %d MB" %
                       (pkgobj.size / 1024 / 1024, fs_size / 1024 / 1024))
                logger.log(logging.ERROR, msg)
                return False
        return True

    def downloadPackage(self, pkgobj=None):
        if not pkgobj:
            raise Exception(_('No package object.'))

        try:
            if not self.isSpaceToDownloadPackage(pkgobj):
                err = _("Insufficient space to download package %s to %s" %
                       (pkgobj, pkgobj.localPkg()))
                raise Exception(err)

            errors = self.downloadPkgs([pkgobj])
            if errors:
                raise Exception("\n".join(errors[pkgobj]))
        except Exception, e:
            print(_("ERROR: %s" % e))
            logger.log(logging.ERROR, e)
            return None

        if hasattr(pkgobj, 'localpath'):
            return pkgobj.localpath
        else:
            return None

    def _extractKernelDebug(self, pkgobj=None, kernelext_dir=None):
        # TODO: Consider 're' match here to ensure it's a kernel
        # debuginfo
        location = self.downloadPackage(pkgobj)
        vmlinuxfound = None

        if location:
            try:
                for path in pkgobj.filelist:
                    if path.endswith('vmlinux'):
                        vmlinuxfound = path
                        break
            except Exception, e:
                print(_("ERROR: %s" % e))
                logger.log(logging.ERROR, e)

        if not vmlinuxfound:
            err = _('Failed to install kernel debug symbols from %s' % pkgobj)
            print(_("ERROR: %s" % err))
            logger.log(logging.ERROR, err)
            raise Exception(err)
            return None

        if hasattr(pkgobj, 'nvr'):
            pkgnvr = pkgobj.nvr
        else:
            pkgnvr = "%s-%s-%s" % (pkgobj.name, pkgobj.version, pkgobj.release)
        destdir = os.path.join(kernelext_dir, pkgnvr)
        dest = os.path.join(destdir, 'vmlinux')
        if os.path.exists(dest):
            logger.log(logging.INFO, "%s already exists, skipping extraction"
                       % dest)
            return dest
        elif not os.path.exists(destdir):
            os.mkdir(destdir)

        return self.extractFile(location, vmlinuxfound, dest)

    def extractKernelDebugs(self, pkgAry):
        extracted_paths = []

        kernelext_dir = confighelper.get_config_helper().get(
                                            option='kern_debug_dir')

        if not os.path.exists(kernelext_dir):
            err = _('Unable to download kernel debug symbols because the '
                    'cache directory, %s, does not exist.') % \
                    (kernelext_dir)
            print err
            logger.log(logging.ERROR, err)
            raise Exception(err)
        # Is the destination director writeable?
        if not os.access(kernelext_dir, os.W_OK):
            err = \
            _('Unable to download kernel debug symbols because the '
              'cache directory, %s, is not writeable.') % \
                (kernelext_dir)
            print err
            logger.log(logging.ERROR, str)
            raise Exception(err)

        for pkgobj in pkgAry:
            ret = self._extractKernelDebug(pkgobj, kernelext_dir)
            if ret:
                if hasattr(pkgobj, 'nvr'):
                    pkgnvr = pkgobj.nvr
                else:
                    pkgnvr = "%s-%s-%s" % (pkgobj.name,
                                           pkgobj.version,
                                           pkgobj.release)
                extracted_paths.append({'package': pkgnvr,
                                        'path': ret})

        return extracted_paths

    def extractFile(self, pkgloc, pattern, dest):
        cpiopattern = "." + pattern
        rpm2cpiocmd = ["rpm2cpio", pkgloc]
        cpiocmd = ["cpio", "-id", cpiopattern]
        tempdir = None

        # Record current working directory, create a temp directory
        # and change to it for CPIO expansion.
        prevcwd = os.getcwd()

        try:
            tempdir = tempfile.mkdtemp('-rhst')
            os.chdir(tempdir)

            # BZ983909 - don't use shell=True
            proc1 = subprocess.Popen(rpm2cpiocmd,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
            proc2 = subprocess.Popen(cpiocmd, stdin=proc1.stdout,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
            # pylint: disable= E1101
            out, err = proc2.communicate()
            ret = proc2.returncode
            if ret != 0:
                raise Exception(err.rstrip())

            # Return to previous dir, move the file to destination
            # and revert to previous cwd.
            shutil.move(os.path.join(tempdir, cpiopattern), dest)
        # pylint: disable=W0703
        except Exception, e:
            logger.log(logging.ERROR, e)
            print(_("ERROR: %s" % e))
            print(_("ERROR: Unable to extract %s from %s" % (pattern, pkgloc)))
            if os.path.exists(dest):
                # clean up in case vmlinux file is only partially extracted
                shutil.rmtree(os.path.dirname(dest))
            dest = None

        os.chdir(prevcwd)
        if tempdir:
            shutil.rmtree(tempdir)

        return dest
