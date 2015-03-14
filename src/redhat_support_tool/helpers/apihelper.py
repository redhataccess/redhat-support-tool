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
A helper class to create an single instance of the redhat_support_lib
API object.
'''


from redhat_support_lib.api import API
import redhat_support_tool.helpers.confighelper as confighelper
import redhat_support_tool.helpers.version as version
import logging

__author__ = 'Keith Robertson <kroberts@redhat.com>'
USER_AGENT = 'redhat-support-tool-%s' % (version.version)
_api = None
logger = logging.getLogger("redhat_support_tool.plugins.list_cases")


def _make_api():
    cfg = confighelper.get_config_helper()

    logger.log(logging.DEBUG, 'user(%s)' % cfg.get(option='user'))
    logger.log(logging.DEBUG, 'proxy_url(%s)' % cfg.get(option='proxy_url'))
    logger.log(logging.DEBUG, 'proxy_user(%s)' % cfg.get(option='proxy_user'))
    '''
    logger.log(logging.DEBUG, 'password(%s)' % cfg.pw_decode(cfg.get(option='password'),
                                                             cfg.get(option='user')))
    logger.log(logging.DEBUG, 'proxy_password(%s)' % cfg.pw_decode(
                                                     cfg.get(option='proxy_password'),
                                                     cfg.get(option='proxy_user')))
    '''
    global _api
    if not _api:
        try:
            url = cfg.get(option='url')
            user = cfg.get(option='user')
            passwd = cfg.pw_decode(cfg.get(option='password'), cfg.get(option='user'))

            # ensure we have a userid
            if user == None or user == '':
                user = cfg.prompt_for_user()

            # ensure we have a password
            if passwd == None or passwd == '':
                passwd = cfg.prompt_for_password()

            if cfg.get(option='no_verify_ssl'):
                no_verify_ssl = True
            else:
                no_verify_ssl = False

            ssl_ca = cfg.get(option='ssl_ca')

            if url:
                _api = API(username=cfg.get(option='user'),
                               password=cfg.pw_decode(cfg.get(option='password'),
                                                      cfg.get(option='user')),
                               url=url,
                               proxy_url=cfg.get(option='proxy_url'),
                               proxy_user=cfg.get(option='proxy_user'),
                               proxy_pass=cfg.pw_decode(cfg.get(option='proxy_password'),
                                                        cfg.get(option='proxy_user')),
                               userAgent=USER_AGENT,
                               no_verify_ssl=no_verify_ssl,
                               ssl_ca=ssl_ca)
            else:
                _api = API(username=cfg.get(option='user'),
                               password=cfg.pw_decode(cfg.get(option='password'),
                                                      cfg.get(option='user')),
                               proxy_url=cfg.get(option='proxy_url'),
                               proxy_user=cfg.get(option='proxy_user'),
                               proxy_pass=cfg.pw_decode(cfg.get(option='proxy_password'),
                                                        cfg.get(option='proxy_user')),
                               userAgent=USER_AGENT,
                               no_verify_ssl=no_verify_ssl,
                               ssl_ca=ssl_ca)
        except:
            # Ideally we could just get rid of this try: except: block as it
            # does absolutely nothing!
            raise
    return _api


def get_api():
    '''
    A helper method to get the API object.
    '''
    # Tell python we want the *global* version and not a
    # function local version. Sheesh. :(
    global _api
    if not _api:
        _api = _make_api()
    return _api


def disconnect_api():
    '''
    Gracefully shutdown the API.
    '''
    global _api
    if _api:
        _api.disconnect()
        _api = None
