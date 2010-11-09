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


import lxml.html

from .iparser import IParser


__all__ = ['LxmlHtmlParser', 'select', 'SelectElementException']


class SelectElementException(Exception):
    pass


def select(element, selector, nb=None, method='cssselect'):
    """
    Select one or many elements from an element, using lxml cssselect by default.

    Raises SelectElementException if not found.

    @param element [obj]  element on which to apply selector
    @param selector [str]  CSS or XPath expression
    @param method [str]  (cssselect|xpath)
    @param nb [int]  number of elements expected to be found.
                     Use None for undefined number, and 'many' for 1 to infinite.
    @return  one or many Element
    """
    if method == 'cssselect':
        results = element.cssselect(selector)
        if nb is None:
            return results
        elif isinstance(nb, basestring) and nb == 'many':
            if results is None or len(results) == 0:
                raise SelectElementException('Element not found with selector "%s"' % selector)
            elif len(results) == 1:
                raise SelectElementException('Only one element found with selector "%s"' % selector)
            else:
                return results
        elif isinstance(nb, int) and nb > 0:
            if results is None:
                raise SelectElementException('Element not found with selector "%s"' % selector)
            elif len(results) < nb:
                raise SelectElementException('Not enough elements found (%d expected) with selector "%s"' % (nb, selector))
            else:
                return results[0] if nb == 1 else results
        else:
            raise Exception('Unhandled value for kwarg "nb": %s' % nb)
    else:
        raise NotImplementedError('Only cssselect method is implemented for the moment')


class LxmlHtmlParser(IParser):
    """
    Parser using lxml.

    Note that it is not available on every systems.
    """

    def parse(self, data, encoding=None):
        if encoding is None:
            parser = None
        else:
            parser = lxml.html.HTMLParser(encoding=encoding, strip_cdata=False)
        return lxml.html.parse(data, parser)

    def tostring(self, element):
        return lxml.html.tostring(element, encoding=unicode)
