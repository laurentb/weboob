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


from .standard import _Selector, _NO_DEFAULT, Filter, FilterError


__all__ = ['CSS', 'XPath', 'XPathNotFound', 'AttributeNotFound', 'Attr', 'Link']


class XPathNotFound(FilterError):
    pass


class AttributeNotFound(FilterError):
    pass


class CSS(_Selector):
    @classmethod
    def select(cls, selector, item):
        return item.cssselect(selector)


class XPath(_Selector):
    pass


class Attr(Filter):
    def __init__(self, selector, attr, default=_NO_DEFAULT):
        super(Attr, self).__init__(selector, default=default)
        self.attr = attr

    def filter(self, el):
        try:
            return u'%s' % el[0].attrib[self.attr]
        except IndexError:
            return self.default_or_raise(XPathNotFound('Unable to find link %s' % self.selector))
        except KeyError:
            return self.default_or_raise(AttributeNotFound('Link %s does not has attribute %s' % (el[0], self.attr)))


class Link(Attr):
    """
    Get the link uri of an element.

    If the <a> tag is not found, an exception IndexError is raised.
    """

    def __init__(self, selector=None, default=_NO_DEFAULT):
        super(Link, self).__init__(selector, 'href', default=default)
