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
from redhat_support_tool.helpers.confighelper import EmptyValueError, _
from redhat_support_tool.plugins import Plugin
import logging
import redhat_support_tool.helpers.common as common
import redhat_support_tool.helpers.confighelper as confighelper
import os


__author__ = 'Keith Robertson <kroberts@redhat.com>'
__author__ = 'Rex White <rexwhite@redhat.com>'

logger = logging.getLogger("redhat_support_tool.plugins.config")


class Config(Plugin):
    plugin_name = 'config'

    @classmethod
    def get_usage(cls):
        '''
        The usage statement that will be printed by OptionParser.

        Example:
            - %prog -c CASENUMBER [options] <comment text here>
        Important: %prog is a OptionParser built-in.  Use it!
        '''
        return _('%prog [options] config.option <new option value>')

    @classmethod
    def get_desc(cls):
        '''
        The description statement that will be printed by OptionParser.

        Example:
            - 'Use the \'%s\' command to add a comment to a case.'\
             % cls.plugin_name
        '''
        return _('Use the \'%s\' command to set or get configuration '
                 'file values.') % cls.plugin_name

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
        options = _('\nThe configuration file options which can be set are:\n')

        # query plugins for list of options
        plugins = common.get_plugin_dict()
        for p_name, p_class in plugins.items():
            func = getattr(p_class, 'config_help')
            options = options + func()

        return _('%s\n'
                 'Examples:\n'
                 '- %s user\n'
                 '- %s user my-rhn-username\n'
                 '- %s --unset user\n') % \
                 (options, cls.plugin_name, cls.plugin_name, cls.plugin_name)

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
        return [Option("-g", "--global", dest="global",
                        help=_('Save configuration option in %s.' %
                               confighelper.ConfigHelper.GLOBAL_CONFIG_FILE),
                        action="store_true",
                        default=False),
                Option("-u", "--unset", dest="unset",
                       help=_('Unset configuration option.'),
                       action="store_true", default=False)]

    #
    #  Methods related to intrinsic configuration options
    #

    @classmethod
    def config_help(self):
        '''
        Return descriptions for all the intrinsic configuration options
        '''
        options = " %-10s: %-67s\n" % \
            ('user', 'The Red Hat Customer Portal user.')
        options = options + " %-10s: %-67s\n" % \
            ('password', 'The Red Hat Customer Portal password.')
        options = options + " %-10s: %-67s\n" % \
            ('debug', 'CRITICAL, ERROR, WARNING, INFO, or DEBUG')
        options = options + " %-10s: %-67s\n" % \
            ('url', _('The support services URL.  Default=%s') % \
             confighelper.ConfigHelper.DEFAULT_URL)
        options = options + " %-10s: %-67s\n" % \
            ('proxy_url', _('A proxy server URL.'))
        options = options + " %-10s: %-67s\n" % \
            ('proxy_user', _('A proxy server user.'))
        options = options + " %-10s: %-67s\n" % \
            ('proxy_password', _('A password for the proxy server user.'))
        options += " %-10s: %-67s\n" % ('ssl_ca',
           _('Path to certificate authorities to trust during communication.'))
        options += " %-10s: %-67s\n" % ('kern_debug_dir',
           _('Path to the directory where kernel debug symbols should be '
             'downloaded and cached. Default=%s') %
            confighelper.ConfigHelper.DEFAULT_KERN_DEBUG_DIR)

        return options

    @classmethod
    def config_get_user(cls):
        cfg = confighelper.get_config_helper()
        return cfg.get(section='RHHelp', option='user')

    @classmethod
    def config_set_user(cls, user, global_config=False):
        cfg = confighelper.get_config_helper()
        cfg.set(section='RHHelp', option='user', value=user,
                persist=True, global_config=global_config)

    @classmethod
    def config_set_password(cls, global_config=False):
        cfg = confighelper.get_config_helper()
        cfg.prompt_for_password(prompt=False, global_config=global_config)

    @classmethod
    def config_get_debug(cls):
        cfg = confighelper.get_config_helper()
        return cfg.get(section='RHHelp', option='debug')

    @classmethod
    def config_set_debug(cls, debug, global_config=False):
        if debug in logging._levelNames:
            cfg = confighelper.get_config_helper()
            cfg.set(section='RHHelp', option='debug', value=debug,
                    persist=True, global_config=global_config)
        else:
            raise EmptyValueError(_('%s is not a valid logging level.') %
                                   debug)

    @classmethod
    def config_get_url(cls):
        cfg = confighelper.get_config_helper()
        return cfg.get(section='RHHelp', option='url')

    @classmethod
    def config_set_url(cls, url, global_config=False):
        cfg = confighelper.get_config_helper()
        cfg.set(section='RHHelp', option='url', value=url, persist=True,
                global_config=global_config)

    @classmethod
    def config_get_proxy_url(cls):
        cfg = confighelper.get_config_helper()
        return cfg.get(section='RHHelp', option='proxy_url')

    @classmethod
    def config_set_proxy_url(cls, url, global_config=False):
        cfg = confighelper.get_config_helper()
        cfg.set(section='RHHelp', option='proxy_url', value=url, persist=True,
                global_config=global_config)

    @classmethod
    def config_get_proxy_user(cls):
        cfg = confighelper.get_config_helper()
        return cfg.get(section='RHHelp', option='proxy_user')

    @classmethod
    def config_set_proxy_user(cls, user, global_config=False):
        cfg = confighelper.get_config_helper()
        cfg.set(section='RHHelp', option='proxy_user', value=user,
                persist=True, global_config=global_config)

    @classmethod
    def config_set_proxy_password(cls, global_config=False):
        cfg = confighelper.get_config_helper()
        cfg.prompt_for_proxy_password(prompt=False,
                                      global_config=global_config)

    @classmethod
    def config_get_ssl_ca(cls):
        cfg = confighelper.get_config_helper()
        return cfg.get(section='RHHelp', option='ssl_ca')

    @classmethod
    def config_set_ssl_ca(cls, ssl_ca, global_config=False):
        cfg = confighelper.get_config_helper()
        if not os.access(ssl_ca, os.R_OK):
            msg = _('Unable to read certificate at %s') % (ssl_ca)
            print msg
            raise Exception(msg)
        cfg.set(section='RHHelp', option='ssl_ca', value=ssl_ca,
                persist=True, global_config=global_config)

    @classmethod
    def config_get_kern_debug_dir(cls):
        cfg = confighelper.get_config_helper()
        return cfg.get(section='RHHelp', option='kern_debug_dir')

    @classmethod
    def config_set_kern_debug_dir(cls, kern_debug_dir, global_config=False):
        cfg = confighelper.get_config_helper()
        cfg.set(section='RHHelp', option='kern_debug_dir',
                value=kern_debug_dir, persist=True,
                global_config=global_config)



    #
    # Main logic
    #

    def validate_args(self):
        if not self._args:
            msg = _('ERROR: %s requires the name of an option to be '
                    'set in the config file.') % self.plugin_name
            print msg
            raise Exception(msg)

    def non_interactive_action(self):
        if self._options['global']:
            global_config = True
        else:
            global_config = False

        # check for display mode
        if len(self._args) == 0:
            # TODO: maybe implement __repr__ on confighelper and print that?
            # get list of global config options
            # get list of local config options

            pass

        # get / set config option...
        else:
            # determine section and option.
            items = self._args[0].split('.')
            if len(items) == 1:
                section = 'RHHelp'
                option = items[0]
            else:
                section = items[0]
                option = items[1]

            # get option's owning class
            if section == 'RHHelp':
                opt_class = self.__class__
            else:
                opt_class = common.get_plugin_dict()[section]

            # process command...
            try:
                # handle 'unset' command
                if self._options['unset']:
                    cfg = confighelper.get_config_helper()
                    cfg.remove_option(section, option, global_config)

                # 'password' is a special case: a one-arg set...
                elif option == 'password':
                    self.config_set_password(global_config=global_config)

                # 'proxy_password' is the other special case: a one-arg set...
                elif option == 'proxy_password':
                    self.config_set_proxy_password(global_config=global_config)

                # is this a 'set' or a 'get'?
                # 'gets' have one arg...
                elif len(self._args) == 1:
                    func = getattr(opt_class, 'config_get_' + option)
                    print func()

                #  ... 'sets' will have two args
                elif len(self._args) == 2:
                    func = getattr(opt_class, 'config_set_' + option)
                    func(self._args[1], global_config=global_config)

            except AttributeError:
                msg = _('ERROR: %s is not a valid configuration file option.')\
                    % self._args[0]
                print msg
                logger.log(logging.WARNING, msg)
                raise
            except EmptyValueError, eve:
                print eve
                logger.log(logging.WARNING, eve)
                raise
            except Exception, e:
                logger.log(logging.WARNING, e)
                raise

        return
