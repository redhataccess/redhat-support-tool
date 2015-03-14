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

from redhat_support_tool.helpers.confighelper import _
from redhat_support_tool.symptoms import AnalyzerPlugin
try:
    from pyparsing import Word, Suppress, Combine, SkipTo, Regex, nums, \
    LineStart
except ImportError:
    from redhat_support_tool.tools.pyparsing import Word, Suppress, Combine, \
        SkipTo, Regex, nums, LineStart
__author__ = 'Dan Varga <dvarga@redhat.com>'
__author__ = 'Keith Robertson <kroberts@redhat.com>'


class JavaStackTraceAnalyzer(AnalyzerPlugin):
    '''
    This is a pyparsing expression that will match Java Stack Traces
    that exist in a text file
    '''

    @classmethod
    def get_symptom(self):
        loglevel = LineStart() + Word(nums)
        analyze_expression = Combine(Regex(".*Exception:") +
                                     SkipTo(Suppress(loglevel), include=True))
        return analyze_expression

    @classmethod
    def get_desc(cls):
        '''
        Simple explanation on what the expression tries to find at a high level
        '''
        return _('This analyzer attempts to locate faults which match the '
                 'typical Java stack trace pattern.')

    @classmethod
    def get_sample(cls):
        '''
        A sample pattern that would produce a match
        '''
        return '''
        Matched Pattern Example:
            javax.el.ELException: java.lang.NullPointerException
            at org.jboss.el.util.ReflectionUtil.invokeMethod(ReflectionUtil.java:339)
            at org.jboss.el.util.ReflectionUtil.invokeMethod(ReflectionUtil.java:280)
            at org.jboss.el.parser.AstMethodSuffix.getValue(AstMethodSuffix.java:59)
            at org.jboss.el.parser.AstMethodSuffix.invoke(AstMethodSuffix.java:65)
        16:08:59,682 ...
        '''

    @classmethod
    def get_name(cls):
        '''
        Human readable name for the expression
        '''
        return _('Java Stack Trace')
