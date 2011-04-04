# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


from dateutil import tz
from logging import warning
import sys
import traceback
import types


__all__ = ['get_backtrace', 'get_bytes_size', 'html2text', 'iter_fields',
            'local2utc', 'to_unicode', 'utc2local', 'limit']


def get_backtrace(empty="Empty backtrace."):
    """
    Try to get backtrace as string.
    Returns "Error while trying to get backtrace" on failure.
    """
    try:
        info = sys.exc_info()
        trace = traceback.format_exception(*info)
        sys.exc_clear()
        if trace[0] != "None\n":
            return "".join(trace)
    except:
        # No i18n here (imagine if i18n function calls error...)
        return "Error while trying to get backtrace"
    return empty


def get_bytes_size(size, unit_name):
    unit_data = {
        'bytes': 1,
        'KB': 1024,
        'MB': 1024 * 1024,
        'GB': 1024 * 1024 * 1024,
        'TB': 1024 * 1024 * 1024 * 1024,
        }
    return float(size * unit_data[unit_name])


try:
    import html2text as h2t
    h2t.UNICODE_SNOB = 1
    h2t.SKIP_INTERNAL_LINKS = True
    html2text = h2t.html2text
except ImportError:
    warning('python-html2text is not present. HTML pages will not be converted into text.')
    def html2text(html):
        return html


def iter_fields(obj):
    for attribute_name in dir(obj):
        if attribute_name.startswith('_'):
            continue
        attribute = getattr(obj, attribute_name)
        if not isinstance(attribute, types.MethodType):
            yield attribute_name, attribute


def local2utc(date):
    date = date.replace(tzinfo=tz.tzlocal())
    date = date.astimezone(tz.tzutc())
    return date


def to_unicode(text):
    r"""
    >>> to_unicode('ascii')
    u'ascii'
    >>> to_unicode(u'utf\xe9'.encode('UTF-8'))
    u'utf\xe9'
    >>> to_unicode(u'unicode')
    u'unicode'
    """
    if isinstance(text, unicode):
        return text
    if not isinstance(text, str):
        text = str(text)
    try:
        return unicode(text, 'utf-8')
    except UnicodeError:
        try:
            return unicode(text, 'iso-8859-1')
        except UnicodeError:
            return unicode(text, 'windows-1252')


def utc2local(date):
    date = date.replace(tzinfo=tz.tzutc())
    date = date.astimezone(tz.tzlocal())
    return date

def limit(iterator, lim):
    count = 0
    iterator = iter(iterator)
    while count < lim:
        yield iterator.next()
        count += 1
    raise StopIteration()
