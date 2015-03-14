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
A module that can redirect a stream to a logger.
'''
import logging
import sys

__author__ = 'Keith Robertson <kroberts@redhat.com>'
logger = logging.getLogger("redhat_support_tool.helpers.StderrLogger")
__stderr_save = sys.stderr


class StderrLogger(object):

    def write(self, buf):
        logger.log(logger.getEffectiveLevel(), buf)

    def flush(self):
        pass


def enableStderrLogger():
    '''
    Some Python modules just won't shut up.  Redirect their stderr to the log
    file.
    '''
    sys.stderr = StderrLogger()


def disableStderrLogger():
    '''
    Re-enable sys.stderr.
    '''
    sys.stderr = __stderr_save
