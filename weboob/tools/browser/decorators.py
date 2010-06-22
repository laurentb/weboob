# -*- coding: utf-8 -*-

# Copyright(C) 2010  Christophe Benz
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


__all__ = ['check_domain', 'id2url']


def check_domain(domain):
    def wrapper(func):
        def inner(self, *args, **kwargs):
            if self.DOMAIN not in args[0]:
                return None
            return func(self, *args, **kwargs)
        return inner
    return wrapper


def id2url(id2url):
    def wrapper(func):
        def inner(self, *args, **kwargs):
            arg = unicode(args[0])
            if arg.startswith('http://'):
                if self.DOMAIN in arg:
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
