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
""" This module manages the configuration for redhat-support-tool.
Configuration options are stored in $HOME/.rhhelp and this module
will both create this configuration file and handle the prompting
of the user for the data which will be stored therein.

To get a configuration you should begin by calling:
 - confighelper.get_config_helper()

This will return an instance of ConfigHelper which has getter
methods for the important configuration options.

"""

from itertools import izip, cycle
import ConfigParser
import base64
import getpass
import gettext
import os
import pwd


__author__ = 'Keith Robertson <kroberts@redhat.com>'
__author__ = 'Rex White <rexwhite@redhat.com>'
t = gettext.translation('redhat-support-tool', fallback=True)
_ = t.ugettext
_config_helper = None
_prompted_for_userid_save = False
_prompted_for_password_save = False


class EmptyValueError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)


class ConfigHelper(object):
    GLOBAL_CONFIG_FILE = "/etc/redhat-support-tool.conf"
    DEFAULT_URL = 'https://api.access.redhat.com'
    DEFAULT_DEBUG = 'WARNING'
    DEFAULT_NOVERIFYSSL = False
    DEFAULT_KERN_DEBUG_DIR = '/var/lib/redhat-support-tool/debugkernels'

    def __init__(self):
        self.global_config = ConfigParser.SafeConfigParser()
        self.local_config = ConfigParser.SafeConfigParser()
        self.private_config = ConfigParser.SafeConfigParser()

        # check for environment variables...
        env_var = os.environ.get("RHST_CONFIG")
        if env_var:
            # override default global config file location
            self.GLOBAL_CONFIG_FILE = env_var

        env_var = os.environ.get("http_proxy")
        if env_var:
            # override config file proxy_url
            self.set(option='proxy_url', value=env_var)

        # get global config items...
        self._load_global_config()

        # get local config items
        self._load_local_config()

        # check for defaults for intrinsic options...
        # make sure we at least have default url and debug options...
        if not self.has_option(option='url'):
            self.set(section='RHHelp', option='url', value=self.DEFAULT_URL,
                     global_config=True, persist=True)

        if not self.has_option(option='debug'):
            self.set(section='RHHelp',
                     option='debug',
                     value=self.DEFAULT_DEBUG,
                     global_config=True,
                     persist=True)

        if not os.path.exists(self.get(option='kern_debug_dir')):
            try:
                os.makedirs(self.get(option='kern_debug_dir'))
            except Exception, e:
                #print _('WARN: Unable to create %s. Message: %s')\
                #    % (self.get(option='kern_debug_dir'), e)
                pass

    def get(self, section='RHHelp', option=None):
        '''
        Returns the string value of 'option' in the indicated section.
        If no section is specified 'RHHelp' is assumed
        If the specified option does not exist in the local config file,
        the value for that option from the global
        config file is returned.  If the option does not exist in either
        config, return None.
        '''
        try:
            # check private config first...
            result = self.private_config.get(section, option)
        except:
            try:
                # check local config...
                result = self.local_config.get(section, option)
            except:
                try:
                    # fall back to global config...
                    result = self.global_config.get(section, option)
                except:
                    result = None

        return result

    def set(self, section='RHHelp', option=None, value=None,
            persist=False, global_config=False):
        '''
        Sets specified 'option' in 'section' to 'value'
        '''

        if global_config:
            config = self.global_config
        elif persist == False:
            config = self.private_config
        else:
            config = self.local_config

        # create section if necessary
        if not config.has_section(section):
            config.add_section(section)

        # add new option
        config.set(section, option, value)

        # save config if persist flag was set
        if persist:
            # save global config
            if global_config:
                self._save_global_config()

            # save local config
            else:
                self._save_local_config()

    def has_option(self, section='RHHelp', option=None):
        '''
        Test for existence of specified option in either local or global config
        '''
        result = False

        # check private config
        if self.private_config.has_option(section, option):
            result = True

        # check local config
        elif self.local_config.has_option(section, option):
            result = True

        # check global config
        elif self.global_config.has_option(section, option):
            result = True

        return result

    def remove_option(self, section='RHHelp', option=None,
                      global_config=False):
        '''
        Remove an option from the indicated configuration
        '''
        if global_config:
            self.global_config.remove_option(section, option)
            self._save_global_config()
        else:
            self.local_config.remove_option(section, option)
            self._save_local_config()

    def _load_local_config(self):
        '''
        Load local config from ~/.redhat-support-tool/redhat-support-tool.conf
        '''
        pw = pwd.getpwuid(os.getuid())
        self.dotdir = os.path.join(pw.pw_dir, '.redhat-support-tool')
        if not os.path.exists(self.dotdir):
            os.makedirs(self.dotdir, 0700)
        self.dotfile = os.path.join(self.dotdir, 'redhat-support-tool.conf')

        self.local_config.read(self.dotfile)

    def _save_local_config(self):
        '''
        Write the local config to
        ~/.redhat-support-tool/redhat-support-tool.conf
        '''
        umask_save = os.umask(0177)  # Set to 600
        try:
            configfile = open(self.dotfile, 'wb', 0600)
            try:
                self.local_config.write(configfile)
            finally:
                configfile.close()
        finally:
            os.umask(umask_save)

    def _load_global_config(self):
        '''
        Load global config from /etc/redhat-support-tool.conf
        '''
        fileAry = self.global_config.read(self.GLOBAL_CONFIG_FILE)
        if len(fileAry) == 0:
            # global config file doesn't exist.
            self.global_config.add_section('RHHelp')
            self.global_config.set('RHHelp', 'url', self.DEFAULT_URL)
            self.global_config.set('RHHelp', 'debug', self.DEFAULT_DEBUG)
            self.global_config.set('RHHelp', 'kern_debug_dir',
                                   self.DEFAULT_KERN_DEBUG_DIR)

    def _save_global_config(self):
        '''
        Write global config to /etc/redhat-support-tool.conf
        '''
        umask_save = os.umask(0173)  # Set to 601
        try:
            configfile = open(self.GLOBAL_CONFIG_FILE, 'wb', 0601)
            try:
                self.global_config.write(configfile)
            finally:
                configfile.close()
        finally:
            os.umask(umask_save)

    def __xor(self, salt, string):
        '''
        A simple utility function to obfuscate the password when a user
        elects to save it in the config file.  We're not necessarily
        going for strong encryption here (eg. a keystore) because that
        would require a user supplied PW to unlock the keystore.

        We're merely trying to provide a convenience against an
        accidental display of the file (eg. cat ~/.rhhelp).
        '''
        str_ary = []
        for x, y in izip(string, cycle(salt)):
            str_ary.append(chr(ord(x) ^ ord(y)))
        return ''.join(str_ary)

    def pw_decode(self, password, key):
        '''
        This convenience function will de-obfuscate a password or other value
        previously obfuscated with pw_encode()

        Returns the de-obfuscated string
        '''
        if password and key:
            password = base64.urlsafe_b64decode(password)
            return self.__xor(key, password)
        else:
            return None

    def pw_encode(self, password, key):
        '''
        This convenience function will obfuscated a password or other value

        Returns the obfuscated string
        '''
        if password and key:
            passwd = self.__xor(key, password)
            return base64.urlsafe_b64encode(passwd)
        else:
            return None

    def get_from_prompt(self, msg, default=None, prompter=raw_input):
        try:
            val = prompter(msg)
            if str(val).strip() == '':
                return default
            else:
                return val
        except EOFError:
            print
            return default

    def prompt_for_user(self):
        # see if we need to prompt the user to save the userid
        global _prompted_for_userid_save
        prompt_for_save = not _prompted_for_userid_save

        # prompt for userid...
        user = self.get_from_prompt(_('Please enter your RHN user ID: '))

        if user and str(user).strip():
            user = str(user).strip()

        if user:
            persist = False
            if prompt_for_save:
                val = self.get_from_prompt(_('Save the user ID in %s (y/n): ')
                                           % (self.dotfile), 'n')
                _prompted_for_userid_save = True
                if str(val).strip().lower() == 'y':
                    persist = True

            self.set(section='RHHelp', option='user',
                     value=user, persist=persist)

        else:
            raise EmptyValueError(_('The RHN user ID cannot be empty.'))

        return user

    def prompt_for_password(self, prompt=True, global_config=False):
        # see if we need to prompt the user to save the password
        global _prompted_for_password_save

        if prompt and not _prompted_for_password_save:
            prompt_for_save = True
            persist = False
        else:
            prompt_for_save = False
            persist = True

        user = self.get(option='user')

        # prompt for password...
        password = self.get_from_prompt(_('Please enter the password for %s: ')
                                        % user, None, getpass.getpass)

        if password:
            if prompt_for_save:
                val = self.get_from_prompt(_(
                                'Save the password for %s in %s (y/n): ') % \
                                (user, self.dotfile), 'n')
                _prompted_for_passwd_save = True
                if str(val).lower() == 'y':
                    persist = True

            passwd = self.pw_encode(password, user)
            self.set(section='RHHelp', option='password', value=passwd,
                     persist=persist, global_config=global_config)

        else:
            raise EmptyValueError(_('The RHN password cannot be empty.'))

        return password

    def prompt_for_proxy_password(self, prompt=True, global_config=False):
        user = self.get(option='proxy_user')

        # prompt for proxy password...
        password = self.get_from_prompt(_(
                            'Please enter the password for proxy user %s: ')
                            % user, None, getpass.getpass)

        if password:
            if prompt:
                persist = False
                val = self.get_from_prompt(_(
                    'Save the password for proxy user %s in %s (y/n): ') % \
                    (user, self.dotfile), 'n')
                if str(val).lower() == 'y':
                    persist = True
            else:
                # if we were asked not to prompt the user about saving
                # go ahead and save!
                persist = True

            passwd = self.pw_encode(password, user)
            self.set(section='RHHelp', option='proxy_password', value=passwd,
                     persist=persist, global_config=global_config)

        else:
            raise EmptyValueError(_('The proxy password cannot be empty.'))

        return password


def get_config_helper():
    '''
    A helper method to get the configuration object.
    '''
    # Tell python we want the *global* version and not a
    # function local version. Sheesh. :(
    global _config_helper
    if not _config_helper:
        _config_helper = ConfigHelper()
    return _config_helper
