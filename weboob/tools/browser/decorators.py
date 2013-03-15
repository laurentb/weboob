# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Christophe Benz, Laurent Bachelier
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.


__all__ = ['check_url', 'id2url']

from urlparse import urlsplit
import re


class check_url(object):
    """
    Checks if the first argument matches the given regular expression (given as str,
    without the ^$ delimiters which are automatically added).
    If not, this decorator will return None instead of calling the function.
    """

    def __init__(self, regexp):
        self.regexp = re.compile('^%s$' % regexp)

    def __call__(self, func):
        def wrapper(funcself, *args, **kwargs):
            if self.regexp.match(args[0]):
                return func(funcself, *args, **kwargs)
            return None
        return wrapper


def id2url(id2url):
    """
    If the first argument is not an URL, this decorator will try to
    convert it to one, by calling the id2url function.
    If id2url returns None (because the id is invalid), the decorated
    function will not be called and None will be returned.
    If the DOMAIN attribute of the method's class is not empty, it will
    also check it. If it does not match, the decorated function will not
    be called and None will be returned.
    """
    def wrapper(func):
        def inner(self, *args, **kwargs):
            arg = unicode(args[0])
            if arg.startswith('http://') or arg.startswith('https://'):
                domain = urlsplit(arg).netloc
                if not self.DOMAIN or self.DOMAIN == domain or domain.endswith('.'+self.DOMAIN):
                    url = arg
                else:
                    return None
            else:
                url = id2url(arg)
                if url is None:
                    return None
            new_args = [url]
            new_args.extend(args[1:])
            return func(self, *new_args, **kwargs)
        return inner
    return wrapper
