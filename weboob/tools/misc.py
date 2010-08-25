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
import sys
import traceback
import types


__all__ = ['to_unicode', 'local2utc', 'html2text', 'get_backtrace', 'iter_fields']


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
        return unicode(text, "utf8")
    except UnicodeError:
        pass
    return unicode(text, "ISO-8859-1")

def local2utc(d):
    d = d.replace(tzinfo=tz.tzlocal())
    d = d.astimezone(tz.tzutc())
    return d

def utc2local(d):
    d = d.replace(tzinfo=tz.tzutc())
    d = d.astimezone(tz.tzlocal())
    return d

try:
    import html2text as h2t
    h2t.UNICODE_SNOB = 1
    h2t.SKIP_INTERNAL_LINKS = True
    html2text = h2t.html2text
except ImportError:
    def html2text(s):
        return s

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

def iter_fields(obj):
    for attribute_name in dir(obj):
        if attribute_name.startswith('_'):
            continue
        attribute = getattr(obj, attribute_name)
        if not isinstance(attribute, types.MethodType):
            yield attribute_name, attribute

def iternb(it, nb=0):
    """
    Iter 'nb' times on the generator
    """
    i = 0
    for v in it:
        if i >= nb:
            raise StopIteration()
        yield v
        i += 1
