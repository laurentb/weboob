# -*- coding: utf-8 -*-

# Copyright(C) 2014 Romain Bignon
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


from .standard import _Selector, _NO_DEFAULT


__all__ = ['Dict']


class _DictMeta(type):
    def __getitem__(cls, name):
        return cls(name)


class Dict(_Selector):
    __metaclass__ = _DictMeta

    def __init__(self, selector=None, default=_NO_DEFAULT):
        super(Dict, self).__init__(self, default=default)
        self.selector = selector.split('/') if selector is not None else []

    def __getitem__(self, name):
        self.selector.append(name)
        return self

    @classmethod
    def select(cls, selector, item, obj=None, key=None):
        if isinstance(item, dict):
            content = item
        else:
            content = item.el

        for el in selector:
            if el not in content:
                return None

            content = content.get(el)

        return content
