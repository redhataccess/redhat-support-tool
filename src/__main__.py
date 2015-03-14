#!/usr/bin/python
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


from redhat_support_tool.helpers.common import set_docstring
from redhat_support_tool.helpers.confighelper import _
from redhat_support_tool.helpers.constants import Constants
from redhat_support_tool.helpers.launchhelper import LaunchHelper
import redhat_support_tool.helpers.version as version
import cmd
import codecs
import inspect
import locale
import logging.handlers
import os
import pkgutil
import pwd
import redhat_support_tool.helpers.common as common
import redhat_support_tool.helpers.confighelper as confighelper
import redhat_support_tool.plugins
import redhat_support_tool.vendors
import sys

# This is a quite ugly hack, but appears to be the only way to make Python 2.x
# handle utf-8 content/consoles correctly.  The UndefinedVariable @-tag
# changes this from an error condition to a warning in PyDev.
reload(sys)
sys.setdefaultencoding('utf-8')  # @UndefinedVariable


__author__ = 'Keith Robertson <kroberts@redhat.com>'
__author__ = 'Rex White <rexwhite@redhat.com>'

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

logger = None


class RHHelp(cmd.Cmd):
    EXIT_CMD = _('Exit the program.')
    prompt = _('Command (? for help): ')
    intro = _("Welcome to the Red Hat Support Tool.")

    def __init__(self):
        cmd.Cmd.__init__(self)
        confighelper.get_config_helper()
        self._init_logger()
        common.ssl_check()
        common.set_plugin_dict(self._get_plugins())
        self._load_plugins(common.get_plugin_dict())

    def _init_logger(self):
        pw = pwd.getpwuid(os.getuid())
        dotdir = os.path.join(pw.pw_dir, '.redhat-support-tool')
        logging_folder = os.path.join(dotdir, 'logs')
        if not os.path.exists(logging_folder):
            os.makedirs(logging_folder, 0700)
        logging_file = os.path.join(logging_folder, 'red_hat_support_tool.log')
        handler = logging.handlers.RotatingFileHandler(logging_file,
                                                       maxBytes=20000,
                                                       backupCount=5)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logging.root.addHandler(handler)
        stat_info = os.stat(logging_file)
        if(stat_info.st_size > 0):
            logging.root.handlers[0].doRollover()
        # Set default level to WARNING
        logging.root.setLevel(logging.WARNING)
        logging_level = logging.getLevelName(confighelper.get_config_helper()
                                             .get(option='debug'))
        logging.root.setLevel(logging_level)

        global logger
        logger = logging.getLogger("redhat-support-tool.rhhelp")
        logger.setLevel(logging.root.getEffectiveLevel())

    def _init_vendor_packages(self):
        vendor_packages = []
        vendor_plugins = []
        vendor_ignorelist = []

        # pkgutil.walk_packages is only in 2.6+ (maybe 2.5, but we don't use
        # python 2.5)
        # The problem is, for 2.4 (RHEL 5) plugins are forced to be in the
        # same locations, 2.6+ we allow far more acceptable locations, which
        # is anywhere defined in sys.path/PYTHONPATH=
        if sys.version_info[:2] >= (2, 6):
            for pkg in pkgutil.walk_packages(
                                redhat_support_tool.vendors.__path__,
                                redhat_support_tool.vendors.__name__ + '.'):
                # pkg = (pkgutil object, package name, is a package?)
                if pkg[2]:
                    vendor_packages.append(pkg[1])
        else:
            for loc in os.listdir(redhat_support_tool.vendors.__path__[0]):
                if (os.path.isdir(loc) and
                    os.path.exists(os.path.join(loc, '__init__.py'))):
                    vendor_packages.append('redhat_support_tool.vendors.%s' %
                                           loc)

        for package in vendor_packages:
            try:
                __import__(package)
                mod = sys.modules[package]
                if hasattr(mod, 'provided_module'):
                    vendor_plugins.extend(mod.provided_modules)
                if hasattr(mod, 'ignored_modules'):
                    vendor_ignorelist.extend(mod.ignored_modules)
            except AttributeError:
                logger.error(_('Vendor plugin %s was not loaded due to missing'
                               ' metadata'), package)
            except ImportError:
                logging.error(_('Unable to load vendor plugin %s,'
                                ' skipping...'), package)
        logger.log(31, "vendor_plugins(%s)" % (vendor_plugins))
        logger.log(31, "vendor_ignorelist(%s)" % (vendor_ignorelist))
        return vendor_plugins, vendor_ignorelist

    def _get_plugins(self):
        plugin_dict = {}

        package = redhat_support_tool.plugins
        prefix = package.__name__ + "."
        modnames = []
        for filename in os.listdir(package.__path__[0]):
            if (filename.endswith('.py') or filename.endswith('.pyc') and
                filename != '__init__.py'):
                modnames.append(prefix + filename.rsplit('.', 1)[0])
#        for importer, modname, ispkg in pkgutil.iter_modules(package.__path__,
#                                                             prefix):

        # Filter functions for vendor overrides and plugins
        vendor_plugins, ignore_list = self._init_vendor_packages()
        modnames = list(set(modnames) - set(ignore_list))
        modnames.extend(vendor_plugins)
        logger.debug(modnames)

        for modname in modnames:
            logger.log(31, "Found submodule %s" % (modname))
            __import__(modname)
            mod = sys.modules[modname]
            objectAry = inspect.getmembers(mod, inspect.isclass)
            for o in objectAry:
                if (issubclass(o[1], redhat_support_tool.plugins.Plugin) and
                    (o[0] != 'InteractivePlugin' and o[0] != 'Plugin') and
                    not issubclass(o[1],
                                redhat_support_tool.plugins.HiddenCommand) and
                    o[1].__module__ not in ignore_list):
                    # Add import to list
                    logger.log(31, "Adding import %s to"
                    " plugin dictionary" % o[0])
                    plugin_dict[o[1].get_name()] = o[1]
        return plugin_dict

    def _load_plugins(self, plugin_dict):
        for plugin in plugin_dict:
            logger.log(31, "Loading plugin %s" % plugin)
            lh = LaunchHelper(plugin_dict[plugin])
            setattr(self,
                    'do_%s' % plugin,
                    getattr(lh,
                            'run'))
            setattr(self,
                    'help_%s' % plugin,
                    getattr(lh,
                            'help'))

#    def do_makeconfig(self, line):
#        confighelper.get_config_helper()

    def help_makeconfig(self):
        print  _("""Usage: makeconfig

The Red Hat Support Tool saves some configuration options
in $HOME/.rhhelp. Use the 'makeconfig' command to create
the $HOME/.rhhelp configuration file.

This command is only necessary if you prefer to use
the Red Hat Support Tool in the non-interactive mode
(for example: \'redhat-support-tool search rhev\'). The
interactive mode will detect the presence of $HOME/.rhhelp
and create it if necessary.
""")

    #
    # Methods related to shell interaction.  Nothing to see here move
    # along please ;)
    #
    def _invalid(self, line):
        print _('%s is an invalid selection. Type \'help\' to see '
                'valid selections again.') % line

    def emptyline(self):
        '''
        Override the default implementation of emptyline so
        that the last command isn't repeated.
        '''
        return None

    def get_names(self):
        '''
        Override the default implementation of get names so that the
        dynamic methods are seen in the help list.
        '''
        return dir(self)

    def do_help(self, line):
        if line:
            cmd.Cmd.do_help(self, line)
        else:
            common.do_help(self)

    def do_e(self, line):
        return 'EOF'

    @set_docstring(EXIT_CMD)
    def help_e(self):
        print
        print self.EXIT_CMD

    def do_q(self, line):
        return 'EOF'

    @set_docstring(EXIT_CMD)
    def help_q(self):
        print
        self.help_e()

    def do_EOF(self, line):
        # EOF (^D) doesn't start a new line, lets do that
        # so it looks better.
        print
        return 'EOF'

    def do_shell(self, line):
        if len(line) == 0:
            print _("ERROR: No command to run was provided")
            self.help_shell()
        else:
            output = os.popen(line).read()
            print output

    @set_docstring(_('Execute a shell command. You can also use \'!\'.'))
    def help_shell(self):
        print
        print '\n'.join(['shell COMMAND',
                         _('Execute a shell command. You can also use \'!\''),
                         _('Example:'),
                         ' shell ls',
                         ' !ls'])

    def completenames(self, text, *ignored):
        '''
        Override the default implemtation so that we don't return EOF.
        '''
        ary = cmd.Cmd.completenames(self, text, *ignored)
        if 'help' in ary:
            ary.remove('help')
        return ary


def main():
    try:
        if len(sys.argv) > 1:
            common.set_interactive(False)
            if str(sys.argv[1]).lower() == '-h' or str(sys.argv[1]).lower() == '--help':
                common.do_help(RHHelp())
                sys.exit(0)
            if str(sys.argv[1]).lower() == '-v' or str(sys.argv[1]).lower() == '--version':
                print 'redhat-support-tool %s' % (version.version)
                sys.exit(0)
            # Compose input string.
            var = u' '.join([unicode(i, 'utf8') for i in sys.argv[1:]])
            if not sys.stdin.isatty():
                # Do we have piped input?
                data = unicode(sys.stdin.read(), 'utf8')
                var = u'%s %s' % (var, data)
                var = var.strip()
            # Set the locale for cases where the user pipes to
            # a file or grep.  Without this 'print' will throw
            # an exception on unicode chars.
            if not sys.stdout.encoding:
                # Encoding will be None when piped to a program/file
                # ex: redhat-support-tool listcases | grep Title
                sys.stdout = codecs.getwriter(
                                    locale.getpreferredencoding())(sys.stdout)
            if not sys.stdout.isatty():
                # We are piping to a file.  Disable ANSI bolding.
                Constants.BOLD = ''
                Constants.END = ''
            ret = RHHelp().onecmd(var)
            # Some commands return None, some for some reason return '', if
            # we sys.exit('') though, it'll print a blank line and set $? to
            # 1, so lets work around that.
            if ret is not None and ret is not 0 and ret != '':
                sys.exit(ret)
        else:
            RHHelp().cmdloop()
    except KeyboardInterrupt:
        print
    except Exception, e:
        print e
        print _('ERROR: %s') % e

if __name__ == '__main__':
    main()
    pass
