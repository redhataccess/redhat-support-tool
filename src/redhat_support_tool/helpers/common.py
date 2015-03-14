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
A helper module with various global utility functions.
'''

from redhat_support_lib.infrastructure.errors import RequestError, \
    ConnectionError
from redhat_support_tool.helpers.confighelper import EmptyValueError, _
import dateutil.parser as parser
import dateutil.tz as tz
import inspect
import os
import os.path
import redhat_support_tool.helpers.apihelper as apihelper
import redhat_support_tool.helpers.confighelper as confighelper
import re
import logging
import struct
import sys
import tempfile
import textwrap

# To support pagination/obtaining terminal sizes
_terminfosupport = True
try:
    import fcntl  # @UnresolvedImport (PyDev can't always find it)
    import termios
except:
    _terminfosupport = False

_sha256support = False
try:
    from hashlib import sha256
    _sha256support = True
except:
    import sha

__author__ = 'Keith Robertson <kroberts@redhat.com>'
_interactive = True
_plugins = None
logger = logging.getLogger("redhat_support_tool.helpers.common")


def is_interactive():
    '''
    Is redhat-support-tool being run as an interactive shell?

    Example of interactive:
     Welcome to the Red Hat Support Tool.
     Command (? for help):

     Example of non-interactive:
       redhat-support-tool addcomment -c 123456 Here are the logs...
    '''
    return _interactive


def set_interactive(boolean):
    '''
    Set the operating mode.
    '''
    global _interactive
    _interactive = boolean


def set_plugin_dict(plugins):
    '''
    Save the dictionary of plugins
    '''
    global _plugins
    _plugins = plugins


def get_plugin_dict():
    '''
    Get the dictionary of loaded plugins
    '''
    return _plugins


def iso8601tolocal(iso8601):
    '''
    Given an ISO8601 datetime, convert to local.

    Returns:
     Empty string if there is a conversion error.
    '''
    if iso8601:
        try:
            return parser.parse(iso8601).astimezone(
                        tz.tzlocal()).strftime("%a %b %d %H:%M:%S %Z %Y")
        except:
            return ''
    else:
        return ''


def get_products():
    '''
    A utility function to get the available products from the API.
    '''
    api = None
    try:
        api = apihelper.get_api()
        productsAry = api.products.list()
        return productsAry
    except EmptyValueError, eve:
        msg = _('ERROR: %s') % str(eve)
        print msg
        logger.log(logging.WARNING, msg)
        raise
    except RequestError, rerr:
        msg = _('Unable to connect to support services API. '
                'Reason: %s') % rerr.reason
        print msg
        logger.log(logging.WARNING, msg)
        raise
    except ConnectionError:
        msg = _('Problem connecting to the support services '
                'API.  Is the service accessible from this host?')
        print msg
        logger.log(logging.WARNING, msg)
        raise
    except:
        msg = _("Unable to find products")
        print msg
        logger.log(logging.WARNING, msg)
        raise


def print_versions(versionsAry):
    try:
        for index, val in enumerate(versionsAry):
            print ' %-3s %-75s' % (index + 1, val)
    except:
        msg = _('ERROR: problem parsing the versions.')
        print msg
        logger.log(logging.WARNING, msg)
        raise


def print_products(productsAry):
    try:
        for index, val in enumerate(productsAry):
            print ' %-3s %-75s' % (index + 1, val.get_name())
    except:
        # TODO: log this
        msg = _('ERROR: problem parsing the products.')
        print msg
        logger.log(logging.WARNING, msg)
        raise


def get_types():
    '''
    A utility function to get the available type from the API.
    '''
    api = None
    try:
        api = apihelper.get_api()
        typeAry = api.values.getType()
        return typeAry
    except EmptyValueError, eve:
        msg = _('ERROR: %s') % str(eve)
        print msg
        logger.log(logging.WARNING, msg)
        raise eve
    except RequestError, re:
        msg = _('Unable to connect to support services API. '
                'Reason: %s') % re.reason
        print msg
        logger.log(logging.WARNING, msg)
        raise
    except ConnectionError:
        msg = _('Problem connecting to the support services '
                'API.  Is the service accessible from this host?')
        print msg
        logger.log(logging.WARNING, msg)
        raise
    except:
        msg = _("Unable to find type")
        print msg
        logger.log(logging.WARNING, msg)
        raise


def print_types(typesAry):
    try:
        for index, val in enumerate(typesAry):
            print ' %-3s %-75s' % (index + 1, val)
    except:
        msg = _('ERROR: problem parsing the types.')
        print msg
        logger.log(logging.WARNING, msg)
        raise


def get_severities():
    '''
    A utility function to get the available severities from the API.
    '''
    api = None
    try:
        api = apihelper.get_api()
        severitiesAry = api.values.getSeverity()
        severitiesAry = severitiesAry[::-1]
        return severitiesAry
    except EmptyValueError, eve:
        msg = _('ERROR: %s') % str(eve)
        print msg
        logger.log(logging.WARNING, msg)
        raise
    except RequestError, re:
        msg = _('Unable to connect to support services API. '
                'Reason: %s') % re.reason
        print msg
        logger.log(logging.WARNING, msg)
        raise
    except ConnectionError:
        msg = _('Problem connecting to the support services '
                'API.  Is the service accessible from this host?')
        print msg
        logger.log(logging.WARNING, msg)
        raise
    except:
        msg = _("Unable to find severities")
        print msg
        logger.log(logging.WARNING, msg)
        raise


def print_severities(severitiesAry):
    regex = re.compile("\((.+?)\)")
    try:
        for index, val in enumerate(severitiesAry):
            r = regex.search(val)
            print ' %-3s %-75s' % (index + 1, str(r.groups()[0]).strip())
    except:
        msg = _('ERROR: problem parsing the severities.')
        print msg
        logger.log(logging.WARNING, msg)
        raise


def get_statuses():
    '''
    A utility function to get the available statuses from the API.
    '''
    api = None
    try:
        api = apihelper.get_api()
        statusesAry = api.values.getStatus()
        return statusesAry
    except EmptyValueError, eve:
        msg = _('ERROR: %s') % str(eve)
        print msg
        logger.log(logging.WARNING, msg)
        raise
    except RequestError, re:
        msg = _('Unable to connect to support services API. '
                'Reason: %s') % re.reason
        print msg
        logger.log(logging.WARNING, msg)
        raise
    except ConnectionError:
        msg = _('Problem connecting to the support services '
                'API.  Is the service accessible from this host?')
        print msg
        logger.log(logging.WARNING, msg)
        raise
    except:
        msg = _("Unable to find statuses")
        print msg
        logger.log(logging.WARNING, msg)
        raise


def print_statuses(statusesAry):
    try:
        for index, val in enumerate(statusesAry):
            print ' %-3s %-75s' % (index + 1, val)
    except:
        msg = _('ERROR: problem parsing the statuses.')
        print msg
        logger.log(logging.WARNING, msg)
        raise


def get_groups():
    '''
    A utility function to get the available groups from the API.
    '''
    api = None
    try:
        api = apihelper.get_api()
        groupsAry = api.groups.list()
        return groupsAry
    except EmptyValueError, eve:
        msg = _('ERROR: %s') % str(eve)
        print msg
        logger.log(logging.WARNING, msg)
        raise
    except RequestError, re:
        msg = _('Unable to connect to support services API. '
                'Reason: %s') % re.reason
        print msg
        logger.log(logging.WARNING, msg)
        raise
    except ConnectionError:
        msg = _('Problem connecting to the support services '
                'API.  Is the service accessible from this host?')
        print msg
        logger.log(logging.WARNING, msg)
        raise
    except:
        msg = _("Unable to find groups")
        print msg
        logger.log(logging.WARNING, msg)
        raise


def print_groups(groupsAry):
    try:
        for index, val in enumerate(groupsAry):
            print ' %-3s %-75s' % (index + 1, val.get_name())
    except:
        msg = _('ERROR: problem parsing the groups.')
        print msg
        logger.log(logging.WARNING, msg)
        raise


def get_terminfo():
    '''
    A utility function to return information about the terminal as a tuple

    returns:
     - tuple consisting of (height, width, xpixels, ypixels); or
     - None if not interactive, or output is not a tty

    Note:
      xpixels and ypixels is unused in the kernel, and will return 0
    '''

    ret = None

    if is_interactive() and _terminfosupport and sys.stdout.isatty():
        # Get current window size via TIOCGWINSZ method
        # TIOCGWINSZ returns 4 unsigned short values (8 bytes)
        tiocgwinsz_fmt = '4H'
        rawwinsize = fcntl.ioctl(sys.stdout, termios.TIOCGWINSZ, ' ' * 8)
        ret = struct.unpack(tiocgwinsz_fmt, rawwinsize)

    return ret


def set_docstring(doctext):
    def docstring(function):
        function.__doc__ = doctext
        return function
    return docstring


def do_help(clsobj):
    if is_interactive():
        HEADER = _("Documented commands (type help <topic>):")
    else:
        HEADER = _("Documented commands (<topic> -h,--help):")

    ruler = '='

    help_dict = {}

    funcs = dir(clsobj.__class__)

    terminfo = get_terminfo()

    if terminfo:
        termwidth = terminfo[1]
    else:
        termwidth = 80

    if '_get_plugins' in funcs:
        plugin_dict = clsobj._get_plugins()
        for plugin in plugin_dict:
            usage = plugin_dict[plugin].get_desc()
            usage = str(usage).replace('%prog',
                                       plugin_dict[plugin].get_name())
            help_dict[plugin] = usage

    for func in funcs:
        if func[:5] == 'help_':
            item = getattr(clsobj, func)
            docstring = item.__doc__
            if inspect.ismethod(item) and docstring:
                help_dict[func[5:]] = docstring

    longest_cmd = max(len(k) for k in help_dict.keys())

    print
    print HEADER
    print ("%s" % str(ruler * len(HEADER)))
    tuple_ary = sorted(help_dict.iteritems())
    for tpl in tuple_ary:
        output = u'%-*s %-s' % (longest_cmd, tpl[0], tpl[1])
        output_wrapped = textwrap.wrap(output, termwidth,
                                       subsequent_indent=' ' *
                                                (longest_cmd + 1))
        for line in output_wrapped:
            print line


def get_linecount(width, most=True, *args):
    longest_line = None
    for line in args:
        linelen = len(line)

        (div, mod) = linelen / width, linelen % width

        if mod > 0:
            div = div + 1

        if ((longest_line is None) or
            (div > longest_line and most is True) or
            (div < longest_line and most is False)):
            longest_line = div
    return longest_line


def split_file(file_path, chunk_size):
    chunk_num = 1
    chunks = []
    file_name = os.path.basename(file_path)
    file_size = os.stat(file_path).st_size

    tempdir = tempfile.mkdtemp(suffix=".rhst")
    tempdir_statvfs = os.statvfs(tempdir)
    tempdir_free = tempdir_statvfs.f_bavail * tempdir_statvfs.f_frsize
    if (tempdir_free < file_size):
        print _('Not enough space available in /tmp to split %s') % (file_name)
        while True:
            line = raw_input(_('Please provide an alternative location to'
                               ' split the file: '))
            line = str(line).strip()
            tempdir = os.path.expanduser(line)
            try:
                os.mkdir(tempdir)
                tempdir_statvfs = os.statvfs(tempdir)
                tempdir_free = (tempdir_statvfs.f_bavail *
                                tempdir_statvfs.f_frsize)
                if (tempdir_free < file_size):
                    print _('Not enough space available in %s, %d bytes'
                            ' required') % (tempdir, file_size)
                else:
                    continue
            except OSError:
                print _('Unable to create directory at %s') % (tempdir)

    in_file = open(file_path)
    while True:
        msg = ''
        shasum = None
        if _sha256support:
            shasum = sha256()
            msg = _('SHA256: %s')
        else:
            shasum = sha.new()
            msg = _('SHA1: %s')
        data = in_file.read(chunk_size)
        if not data:
            break
        out_filename = os.path.join(tempdir, "%s.%03d" % (file_name,
                                                          chunk_num))
        out_file = open(out_filename, 'w')
        out_file.write(data)

        shasum.update(data)

        chunks.append({'file': out_filename,
                       'msg': msg % (shasum.hexdigest())})
        chunk_num += 1

    return chunks


def ssl_check():
    '''Check SSL configuration options

    Will print warnings for various potentially unsafe situations as a means
    to alert of possible Man-in-the-Middle vectors, or SSL communication is
    likely to fail.'''
    # Import confighelper - we need to know how various bits are configured.
    cfg = confighelper.get_config_helper()
    if cfg.get(option='no_verify_ssl'):
        # Unsafe/Not Recommended. Warn user, suggest loading the CA cert for
        # the proxy/server
        msg = _('Warning: no_ssl_verify is enabled in the Red Hat Support Tool'
                ' configuration, this may allow other servers to intercept'
                ' communications with Red Hat.  If you have a transparent SSL'
                ' proxy server, you can trust it\'s Certificate Authority'
                ' using: \'config ssl_ca <filepath>\'')
        logging.warn(msg)
        print msg
    elif (cfg.get(option='ssl_ca')
          and not os.access(cfg.get(option='ssl_ca'), os.R_OK)):
        # Customer has configured a path to a CA certificate to trust, but we
        # can't find or access the Certificate Authority file that we will pass
        # to the API.  It's not a failure, but we should warn, in case they do
        # use Red Hat APIs
        msg = _('Warning: Red Hat Support Tool is unable to access the'
                ' designated Certificate Authority certificate for server'
                ' verification at %s.  Please correct/replace this file,'
                ' otherwise functionality may be limited.')
        logging.warn(msg)
        print msg
    return

def get_friendly_file_length(file_len):
    '''
    A utility function to return a more human friendly file length string.
    '''
    len_str = "%s bytes" % file_len
    if file_len >= 1024*1024:
        len_str += " (%s MB)" % (file_len/1024/1024)
    elif file_len >= 1024:
        len_str += " (%s KB)" % (file_len/1024)
    return len_str

def str_to_bool(s):
    '''
    Converts a string representing a boolean to an actual boolean
    '''
    if isinstance(s, bool):
        return s
    if not isinstance(s, str):
        return None

    s = s.strip().lower()
    if s in ['false', 'f', 'no', 'n', '0']:
        return False
    if s in ['true', 't', 'yes', 'y', '1']:
        return True
    return None
