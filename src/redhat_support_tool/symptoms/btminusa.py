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
    from pyparsing import Word, Suppress, Combine, SkipTo, Regex, Literal
except ImportError:
    from redhat_support_tool.tools.pyparsing import \
    Word, Suppress, Combine, SkipTo, Regex, Literal

__author__ = 'Dan Varga <dvarga@redhat.com>'


class BtMinusA(AnalyzerPlugin):
    '''
    This is a pyparsing expression that will match bt -a output
    that exist in a text file
    '''

    @classmethod
    def get_symptom(self):
        quitline = Literal("crash> quit")
        analyze_expression = Combine(Regex(".*KERNEL:") +
                                     SkipTo(Suppress(quitline), include=True))
        return analyze_expression

    @classmethod
    def get_desc(cls):
        '''
        Simple explanation on what the expression tries to find at a high level
        '''
        return _('This analyzer attempts to locate bt -a output.')

    @classmethod
    def get_sample(cls):
        '''
        A sample pattern that would produce a match
        '''
        return '''
Matched Pattern Example:
KERNEL: /var/lib/redhat-support-tool/debugkernels/2.6.32-279.el6.x86_65-vmlinux
DUMPFILE: /tmp/task_2FNtazG.vmcore  [PARTIAL DUMP]
CPUS: 2
DATE: Thu Nov 29 14:29:44 2012
...
    R10: 00000000ffffffff  R11: 0000000000000246  R12: 0000000000000002
    R13: 00007f072163f780  R14: 0000000000000002  R15: 0000000000000000
    ORIG_RAX: 0000000000000001  CS: 0033  SS: 002b
crash> quit
'''

    @classmethod
    def get_name(cls):
        '''
        Human readable name for the expression
        '''
        return _('Crash bt -a Analyzer')
