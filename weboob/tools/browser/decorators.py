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


__all__ = ['check_domain', 'id2url']

from urlparse import urlsplit

def check_domain(domain):
    def wrapper(func):
        def inner(self, *args, **kwargs):
            if self.DOMAIN not in args[0]:
                return None
            return func(self, *args, **kwargs)
        return inner
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
                if self.DOMAIN and self.DOMAIN == urlsplit(arg).netloc:
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
