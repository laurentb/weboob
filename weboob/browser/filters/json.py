# -*- coding: utf-8 -*-

# Copyright(C) 2014-2015 Romain Bignon, Laurent Bachelier
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


from .standard import _Filter, _NO_DEFAULT, Filter, ParseError

__all__ = ['Dict']


class NotFound(object):
    def __repr__(self):
        return 'NOT_FOUND'

_NOT_FOUND = NotFound()


class _DictMeta(type):
    def __getitem__(cls, name):
        return cls(name)


class Dict(Filter):
    __metaclass__ = _DictMeta

    def __init__(self, selector=None, default=_NO_DEFAULT):
        super(Dict, self).__init__(self, default=default)
        if selector is None:
            self.selector = []
        elif isinstance(selector, basestring):
            self.selector = selector.split('/')
        elif callable(selector):
            self.selector = [selector]
        else:
            self.selector = selector

    def __getitem__(self, name):
        self.selector.append(name)
        return self

    def filter(self, elements):
        if elements is not _NOT_FOUND:
            return elements
        else:
            return self.default_or_raise(ParseError('Element %r not found' % self.selector))

    @classmethod
    def select(cls, selector, item, obj=None, key=None):
        if isinstance(item, (dict, list)):
            content = item
        else:
            content = item.el

        for el in selector:
            if isinstance(content, list):
                el = int(el)
            elif isinstance(el, _Filter):
                el._key = key
                el._obj = obj
                el = el(item)
            elif callable(el):
                el = el(item)

            try:
                content = content[el]
            except (KeyError, IndexError):
                return _NOT_FOUND

        return content
