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
A module to convert recommendations into a Generic Prompt for use by plugins
'''
from collections import deque
from redhat_support_tool.helpers.constants import Constants
from redhat_support_tool.plugins import ObjectDisplayOption
from redhat_support_tool.plugins.kb import Kb
import textwrap

__author__ = 'Nigel Jones <nigjones@redhat.com>'


def generate_metadata(recommendations):
    recommend_opts = deque()
    doc = u''

    for rec in recommendations:
        doc += '%-12s %-60s\n' % ('%s:' % Constants.TITLE,
                                  rec.get_solutionTitle())
        doc += '%-12s %s\n' % (Constants.URL,
                                rec.get_resourceViewURI())
        linktype = ""
        if rec.get_linked():
            linktype = Constants.CASE_REC_LINKED
            doc += '%-12s %-60s\n' % (Constants.CASE_REC_SOURCE,
                                      linktype)
        else:
            linktype = Constants.CASE_REC_UNLINKED
            doc += '%-12s %-60s\n' % (Constants.CASE_REC_SOURCE,
                                      linktype)
        if rec.get_solutionAbstract():
            doc += '%s\n' % (Constants.ABSTRACT)
            doc += textwrap.fill(rec.get_solutionAbstract(),
                                 79,
                                 initial_indent=' ' * 4,
                                 subsequent_indent=' ' * 4)
            doc += '\n\n%s%s%s\n\n' % (Constants.BOLD,
                                    str('-' * Constants.MAX_RULE),
                                    Constants.END)
        # Create a interactive prompt for interactive users.
        disp_opt_text = '[%7s:%s] %s (%s)' % (rec.get_resourceId(),
                        rec.get_solutionKcsState()[0:3].upper(),
                        rec.get_solutionTitle(), linktype)
        obj_disp_opt_metadata = {'pt_str': rec.get_resourceId(),
                                 'pt_obj': None}
        rec_opt = ObjectDisplayOption(disp_opt_text,
                                      'interactive_action',
                                      obj_disp_opt_metadata)
        recommend_opts.append(rec_opt)
    prompt_metadata = {'lhplugin': Kb,
                       'type': Constants.CASE_RECOMMENDATIONS,
                       'options': recommend_opts}

    disp_opt = ObjectDisplayOption(Constants.CASE_RECOMMENDATIONS,
                                   'interactive_action', prompt_metadata)

    return (disp_opt, doc)
