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
try:
    from pyparsing import line, lineno, col
except ImportError:
    from redhat_support_tool.tools.pyparsing import line, lineno, col
import inspect

__author__ = 'Dan Varga <dvarga@redhat.com>'
__author__ = 'Keith Robertson <kroberts@redhat.com>'


class AnalyzerPlugin(object):
    '''
    This is the Base class for all Analyzer Plugins
    Defines the methods all Analyzer plugins must implement
    '''

    symptoms = []
    deduper = None
    # Display name for symptom plugin

    @classmethod
    def get_name(cls):
        return 'OVERRIDE ME: AnalyzerPlugin::get_name'

    # Description of what the symptom plugin is looking for
    @classmethod
    def get_desc(cls):
        return 'OVERRIDE ME: AnalyzerPlugin::get_desc'

    # Get the pyparsing symptom object, this must be overridden
    @classmethod
    def get_symptom(cls):
        return None

    @classmethod
    def get_sample(cls):
        return None

    @classmethod
    def get_symptom_source(cls):
        '''
        A utility method to return the source code of the symptom.
        '''
        return inspect.getsource(cls.get_symptom)

    @classmethod
    def createTokenObject(cls, st, locn, toks):
        '''
        parseString throws an exception immediately if the text does not match,
        but would have returned these tokens
        searchString will keep searching, but wont return the tokens,
        so just gather them all up here and make them available
        after returning from searchString, check
        redhat_support_tool.symptoms.AnalyzerPlugin.symptoms for the actual
        results

        This method will be called for each match found when parsing the file
        Returns: Token object (defined below)
        '''
        if not cls.deduper:
            cls.deduper = dict()

        token = Token(st, locn, toks[0])
        # Only add the token to the list if we haven't seen it before
        if token.token_string in cls.deduper:
            return
        else:
            cls.deduper[token.token_string] = ""
            cls.symptoms.append(token)


class Token(object):
    '''
    This class defines the Token that will contain information about
    each match when parsing a file looking for symptoms
    '''
    def __init__(self, st, locn, tokString):
        self.token_string = tokString
        self.loc = locn
        self.before_line = line(locn - 1, st)
        self.source_line = line(locn, st)
        self.line_num = lineno(locn, st)
        self.col = col(locn, st)
