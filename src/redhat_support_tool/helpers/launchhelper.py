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

import logging
import redhat_support_tool.helpers.common as common
import redhat_support_tool.plugins

__author__ = 'Keith Robertson <kroberts@redhat.com>'
logger = logging.getLogger("redhat_support_tool.helpers.launchhelper")


class LaunchHelper(object):
    plugin_class_ref = None

    def __init__(self, plugin_class_ref):
        '''
        Arguments:
         The plug-in class which will be called.
        '''
        self.plugin_class_ref = plugin_class_ref

    def run(self, line, dispopt=None, pt_exception=False, prompt=None):
        '''
        Creates an initializes the given plug-in in the following
        order.
        1) Create plug-in
        2) Call plug-in's parse_args method.  This will parse STDIN
           from user in plug-in's OptionParser.
        3) Call validate_args.  This is a hook that the plug-in should
           implement to check that the user supplied the requisite number
           of args to actually do something.
        4) Call postinit.  This is a hook that the plug-in can use to
           do something.  At this point the plug-in should know that it
           has enough information to actually do something and can do
           that something.
        5) Depending on the run mode (ie. interactive vs. non-interactive)
           and the type of plug-in the following things will happen:

     Running Mode | Subclass of InteractivePlugin | Methods called
     -----------------------------------------------------------------------
     Interactive  |      True                     |  do_help() <- Print menu
                  |                               |  cmdloop() <- Start submenu
     -----------------------------------------------------------------------
 Non-Interactive  |      True                     |  non_interactive_action()
     -----------------------------------------------------------------------
     Interactive  |      False                    |  non_interactive_action()
     -----------------------------------------------------------------------
 Non-Interactive  |      False                    |  non_interactive_action()

        Arguments:
         line - The STDIN from the user that will be supplied to the
                plug-in.
        :param pt_exception:
            Option to passthrough exceptions to the LaunchHelper.run() caller.
            This allows modules to track exceptions from downstream plugins.

        :type pt_exception: boolean
        '''
        logger.log(logging.DEBUG, line)
        logger.log(logging.DEBUG, dispopt)
        logger.log(logging.DEBUG, pt_exception)
        logger.log(logging.DEBUG, prompt)
        if str(line).lower() == '-h' or str(line).lower() == '--help':
            # We need to intercept these two command
            return self.help()
        else:
            try:
                # Pay close attention here kiddies.  A class reference
                # becomes an object ;)
                cls = self.plugin_class_ref()
                cls.parse_args(line)
                if isinstance(dispopt,
                              redhat_support_tool.plugins.ObjectDisplayOption):
                    # Insert stored object from DisplayOption
                    stored_obj = dispopt.stored_obj
                    cls.insert_obj(stored_obj)
                cls.validate_args()
                ret = cls.postinit()
                if ret is not None and ret is not 0:
                    return ret
                if (common.is_interactive() and
                    issubclass(self.plugin_class_ref,
                               redhat_support_tool.plugins.InteractivePlugin)):
                    if prompt:
                        cls.prompt = prompt
                    if not hasattr(cls, 'no_submenu') or not cls.no_submenu:
                        # pylint: disable=W0212
                        cls._print_submenu()
                        return cls.cmdloop(None)
                else:
                    return cls.non_interactive_action()
            # pylint: disable=W0703
            except Exception, e:
                logger.exception(e)
                if pt_exception:
                    raise

    def help(self):
        print
        try:
            self.plugin_class_ref.show_command_help()
        # pylint: disable=W0703
        except Exception, e:
            logger.log(logging.WARNING, e)
        print
        return ''
