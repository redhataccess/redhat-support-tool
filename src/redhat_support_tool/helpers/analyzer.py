# -*- coding: utf-8 -*-

#
# Copyright (c) 2013 Red Hat, Inc.
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
import redhat_support_tool.symptoms as symptoms
import logging
import os
import sys
import inspect

__author__ = 'Dan Varga <dvarga@redhat.com>'
__author__ = 'Keith Robertson <kroberts@redhat.com>'

logger = logging.getLogger("redhat_support_tool.helper.analyzer")


class Analyzer(object):
    '''
    A helper class to allow the analyzer function to be used
    via redhat-support-tool proper and other redhat-support-tool-*
    projects
    '''
    plugin_dict = {}

    @classmethod
    def load_plugins(cls):
        '''
        Load all of the plugins for the analyzer
        Returns: dict of plugin names that were loaded
        '''
        cls.plugin_dict = cls._get_plugins()
        return cls.plugin_dict

    @classmethod
    def _get_plugins(cls):
        '''
        Real work of loading the plugins done here
        '''
        package = symptoms
        prefix = package.__name__ + "."
        modnames = []
        # Search for files in symptoms/* with .py(c) ignore __init__
        for filename in os.listdir(package.__path__[0]):
            if filename.endswith('.py') or filename.endswith('.pyc') and \
                (filename != '__init__.py' or filename != '__init__.pyc'):
                logger.log(logging.DEBUG, "Found file %s" % filename)
                modnames.append(prefix + filename.rsplit('.', 1)[0])
        # Loop over the located modules
        # to see if they are a subclass of AnalyzerPlugin
        for modname in modnames:
            logger.log(logging.DEBUG, "Found symptom submodule %s" % (modname))
            __import__(modname)
            mod = sys.modules[modname]
            objectAry = inspect.getmembers(mod, inspect.isclass)
            for o in objectAry:
                if issubclass(o[1],
                     symptoms.AnalyzerPlugin) and \
                    (o[0] != 'AnalyzerPlugin'):
                    logger.log(logging.DEBUG, "Adding import %s to"
                    " symptom analyzer plugin dictionary" % o[0])
                    # This is a subclass of AnalyzerPlugin, add it to the list
                    cls.plugin_dict[o[1].get_name()] = o[1]
        return cls.plugin_dict

    @classmethod
    def get_symptom_names(cls):
        '''
        Returns a string list of all available symptoms.

        Example:
        ['Java Stack Trace', 'MCE Error']
        '''
        if not cls.plugin_dict:
            cls.load_plugins()
        return cls.plugin_dict.keys()

    @classmethod
    def get_symptoms(cls):
        '''
        Returns *class* references to the available symptoms.
        '''
        if not cls.plugin_dict:
            cls.load_plugins()
        return cls.plugin_dict.values()

    @classmethod
    def analyze(cls, filename, symptom_list=None):
        '''
        Analyze the contents of the specified file against a list
        of supplied symptoms, or against all symptoms by default
        see symptoms/__init__.py Token class for more information
        Returns: array of symptom tokens found
        '''
        if not cls.plugin_dict:
            cls.load_plugins()

        # Clear out the deduper, not sure if there is a cleaner way to do this
        del symptoms.AnalyzerPlugin.deduper
        symptoms.AnalyzerPlugin.symptoms = []
        symptoms.AnalyzerPlugin.deduper = None

        # Need to build out an "or'ed" together statement
        expression = None
        if symptom_list == None:
            symptom_list = cls.plugin_dict.keys()

        for s in symptom_list:
            logger.log(logging.DEBUG, "Analyze Plugin %s" % s)

        for s in symptom_list:
            if (cls.plugin_dict[s] != None):
                expression = cls.plugin_dict[s].get_symptom()

                # Setup the callback to be able to "Tokenize" the results
                expression.setParseAction(
                                    symptoms.AnalyzerPlugin.createTokenObject)

                # searchString doesn't correctly return the Tokens
                # it's return value is nonsense, just pretend it's not there
                logger.log(logging.DEBUG, "Starting parsing for %s" %
                           cls.plugin_dict[s].get_name())
                try:
                    if os.path.isfile(os.path.expanduser(filename)):
                        expression.searchString(
                                    file(os.path.expanduser(filename)).read())
                    else:
                        expression.searchString(filename)
                except IOError, e:
                    logger.log(logging.ERROR, e)
                    print "Could not open file: %s  Error: %s" \
                        % (e.filename, e.strerror)
                    raise
                except:
                    expression.searchString(filename)
                logger.log(logging.DEBUG, "Ended parsing for %s" %
                           cls.plugin_dict[s].get_name())

        # symptoms.AnalyzerPlugin.symptoms contains the real
        # results from searchString
        return symptoms.AnalyzerPlugin.symptoms
