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
    from pyparsing import Combine, SkipTo, Regex
except ImportError:
    from redhat_support_tool.tools.pyparsing import Combine, \
        SkipTo, Regex

__author__ = 'Dan Varga <dvarga@redhat.com>'
__author__ = 'Keith Robertson <kroberts@redhat.com>'
__author__ = 'Nigel Jones <nigjones@redhat.com>'


class PythonTraceBackAnalyzer(AnalyzerPlugin):
    '''
    This is a pyparsing expression that will match Python Trackbacks
    that exist in a text file
    '''

    @classmethod
    def get_symptom(self):
        analyze_expression = Combine(Regex(r"Traceback.*:") +
                                     SkipTo(Regex(r"\w:.*"),
                                            include=True))
        return analyze_expression

    @classmethod
    def get_desc(cls):
        '''
        Simple explanation on what the expression tries to find at a high level
        '''
        return _('This analyzer attempts to locate faults which match the '
                 'typical Python Traceback pattern.')

    @classmethod
    def get_sample(cls):
        '''
        A sample pattern that would produce a match
        '''
        return '''
Matched Pattern Example:
2013-02-13 15:05:45,904 - launchhelper - ERROR - Installation of debug images
Traceback (most recent call last):
  File ".../redhat_support_tool/helpers/launchhelper.py", line 82, in run
    cls.validate_args()
  File ".../plugins/btextract.py", line 206, in validate_args
    self._find_debug_symbols()
  File ".../plugins/btextract.py", line 192, in _find_debug_symbols
    raise Exception(_('Installation of debug images failed, '
Exception: Installation of debug images failed, cannot proceed
        '''

    @classmethod
    def get_name(cls):
        '''
        Human readable name for the expression
        '''
        return _('Python Trackback')
