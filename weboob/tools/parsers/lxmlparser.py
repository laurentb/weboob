# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Christophe Benz
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


import re
import lxml.html as html
import lxml.etree as etree

from .iparser import IParser
from ..browser import BrokenPageError


__all__ = ['LxmlHtmlParser', 'LxmlXmlParser']


class LxmlParser(IParser):
    """
    Parser using lxml.

    Note that it is not available on every systems.
    """

    def get_parser(encoding=None):
        pass

    def parse(self, data, encoding=None):
        if encoding is None:
            parser = None
        else:
            parser = self.get_parser(encoding=encoding)
        return self.module.parse(data, parser)

    def tostring(self, element):
        return self.module.tostring(element, encoding=unicode)

    def tocleanstring(self, element):
        txt = [txt.strip() for txt in element.itertext()]
        txt = u' '.join(txt)            # 'foo   bar'
        txt = re.sub('\s+', ' ', txt)   # 'foo bar'
        return txt.strip()

    def strip(self, s):
        doc = self.module.fromstring(s)   # parse html/xml string
        return self.tocleanstring(doc)

    @classmethod
    def select(cls, element, selector, nb=None, method='cssselect', **kwargs):
        """
        Select one or many elements from an element, using lxml cssselect by default.

        Raises :class:`weboob.tools.browser.browser.BrokenPageError` if not found.

        :param element: element on which to apply selector
        :type element: object
        :param selector: CSS or XPath expression
        :type selector: str
        :param method: (cssselect|xpath)
        :type method: str
        :param nb: number of elements expected to be found. Use None for
                   undefined number, and 'many' for 1 to infinite
        :type nb: :class:`int` or :class:`str`
        :rtype: Element
        """
        if method == 'cssselect':
            results = element.cssselect(selector, **kwargs)
        elif method == 'xpath':
            results = element.xpath(selector, **kwargs)
        else:
            raise NotImplementedError('Only the cssselect and xpath methods are supported')
        if nb is None:
            return results
        elif isinstance(nb, basestring) and nb == 'many':
            if results is None or len(results) == 0:
                raise BrokenPageError('Element not found with selector "%s"' % selector)
            elif len(results) == 1:
                raise BrokenPageError('Only one element found with selector "%s"' % selector)
            else:
                return results
        elif isinstance(nb, int) and nb > 0:
            if results is None:
                raise BrokenPageError('Element not found with selector "%s"' % selector)
            elif len(results) < nb:
                raise BrokenPageError('Not enough elements found (%d expected) with selector "%s"' % (nb, selector))
            else:
                return results[0] if nb == 1 else results
        else:
            raise Exception('Unhandled value for kwarg "nb": %s' % nb)


class LxmlHtmlParser(LxmlParser):
    """
    Parser using lxml.

    Note that it is not available on every systems.
    """
    def __init__(self, *args, **kwargs):
        self.module = html

    def get_parser(self, encoding=None):
        return html.HTMLParser(encoding=encoding)


class LxmlXmlParser(LxmlParser):
    """
    Parser using lxml.

    Note that it is not available on every systems.
    """
    def __init__(self, *args, **kwargs):
        self.module = etree

    def get_parser(self, encoding=None):
        return etree.XMLParser(encoding=encoding, strip_cdata=False)
