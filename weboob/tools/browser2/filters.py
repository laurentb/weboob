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

from __future__ import absolute_import

from dateutil.parser import parse as parse_date
import datetime
from decimal import Decimal
import re
from weboob.capabilities.base import NotAvailable

_NO_DEFAULT = object()


class _Filter(object):
    _creation_counter = 0

    def __init__(self):
        self._creation_counter = _Filter._creation_counter
        _Filter._creation_counter += 1


class Filter(_Filter):
    """
    Class used to filter on a HTML element given as call parameter to return
    matching elements.

    Filters can be chained, so the parameter supplied to constructor can be
    either a xpath selector string, or an other filter called before.

    >>> from lxml.html import etree
    >>> f = CleanDecimal(CleanText('//p'))
    >>> f(etree.fromstring('<html><body><p>blah: <span>229,90</span></p></body></html>'))
    Decimal('229.90')
    """

    def __init__(self, selector=None):
        super(Filter, self).__init__()
        self.selector = selector

    def __call__(self, item):
        if isinstance(self.selector, basestring):
            value = item.xpath(self.selector)
        elif callable(self.selector):
            value = self.selector(item)
        else:
            value = self.selector

        return self.filter(value)

    def filter(self, value):
        """
        This method have to be overrided by children classes.
        """
        return value


class Env(_Filter):
    """
    Filter to get environment value of the item.

    It is used for example to get page parameters, or when there is a parse()
    method on ItemElement.
    """
    def __init__(self, name):
        super(Env, self).__init__()
        self.name = name

    def __call__(self, item):
        return item.env[self.name]

class TableCell(_Filter):
    """
    Used with TableElement, it get the cell value from its name.

    For example:

        class table(TableElement):
            head_xpath = '//table/thead/th'
            item_xpath = '//table/tbody/tr'

            col_date =    u'Date'
            col_label =   [u'Name', u'Label']

            class item(ItemElement):
                klass = Object
                obj_date = Date(TableCell('date'))
                obj_label = CleanText(TableCell('label'))
    """

    def __init__(self, *names, **kwargs):
        super(TableCell, self).__init__()
        self.names = names
        self.default = kwargs.pop('default', _NO_DEFAULT)

    def __call__(self, item):
        for name in self.names:
            idx = item.parent.get_colnum(name)
            if idx is not None:
                return item.xpath('./td[%s]' % (idx + 1))

        if self.default is not _NO_DEFAULT:
            return self.default
        raise KeyError('Unable to find column %s' % ' or '.join(self.names))

class CleanText(Filter):
    """
    Get a cleaned text from an element.

    It first replaces all tabs and multiple spaces to one space and strip the result
    string.
    Second, it replaces all symbols given in second argument.
    """
    def __init__(self, selector, symbols=''):
        super(CleanText, self).__init__(selector)
        self.symbols = symbols

    def filter(self, txt):
        if isinstance(txt, (tuple,list)):
            txt = ' '.join(map(self.clean, txt))

        txt = self.clean(txt)
        return self.remove(txt, self.symbols)

    @classmethod
    def clean(self, txt):
        if not isinstance(txt, basestring):
            txt = [t.strip() for t in txt.itertext()]
            txt = u' '.join(txt)                 # 'foo   bar'
        txt = re.sub(u'[\s\xa0\t]+', u' ', txt)   # 'foo bar'
        return txt.strip()

    @classmethod
    def remove(self, txt, symbols):
        for symbol in symbols:
            txt = txt.replace(symbol, '')
        return txt

class CleanDecimal(CleanText):
    """
    Get a cleaned Decimal value from an element.
    """
    def filter(self, text):
        text = super(CleanDecimal, self).filter(text)
        text = text.replace('.','').replace(',','.')
        return Decimal(re.sub(u'[^\d\-\.]', '', text))

class Link(Filter):
    """
    Get the link uri of an element.

    If the <a> tag is not found, an exception IndexError is raised.
    """
    def filter(self, el):
        return el[0].attrib.get('href', '')


class Field(_Filter):
    """
    Get the attribute of object.
    """
    def __init__(self, name):
        super(Field, self).__init__()
        self.name = name

    def __call__(self, item):
        return item.use_selector(getattr(item, 'obj_%s' % self.name))


class Regexp(Filter):
    """
    Apply a regex.

    >>> from lxml.html import etree
    >>> f = Regexp(CleanText('//p'), r'Date: (\d+)/(\d+)/(\d+)', '\\3-\\2-\\1')
    >>> f(etree.fromstring('<html><body><p>Date: <span>13/08/1988</span></p></body></html>'))
    u'1988-08-13'
    """
    def __init__(self, selector, pattern, template=None, flags=0, default=_NO_DEFAULT):
        super(Regexp, self).__init__(selector)
        self.pattern = pattern
        self.regex = re.compile(pattern, flags)
        self.template = template
        self.default = default

    def filter(self, txt):
        if isinstance(txt, (tuple,list)):
            txt = ' '.join([t.strip() for t in txt.itertext()])

        mobj = self.regex.search(txt)
        if not mobj:
            if self.default is not _NO_DEFAULT:
                return self.default
            else:
                raise KeyError('Unable to match %s in %r' % (self.pattern, txt))

        if self.template is None:
            return next(g for g in mobj.groups() if g is not None)
        else:
            return mobj.expand(self.template)

class Map(Filter):
    def __init__(self, selector, map, default=_NO_DEFAULT):
        super(Map, self).__init__(selector)
        self.map = map
        self.default = default

    def filter(self, txt):
        try:
            return self.map[txt]
        except KeyError:
            if self.default is not _NO_DEFAULT:
                return self.default
            else:
                raise KeyError('Unable to handle %r' % txt)

class Date(Filter):
    def filter(self, txt):
        if txt is NotAvailable:
            return NotAvailable
        return parse_date(txt)

class Time(Filter):
    def filter(self, txt):
        m = re.search('((?P<hh>\d+):)?(?P<mm>\d+):(?P<ss>\d+)', txt)
        if m:
            hh = int(m.groupdict()['hh'] or 0)
            mm = int(m.groupdict()['mm'] or 0)
            ss = int(m.groupdict()['ss'] or 0)
            return datetime.time(hh, mm, ss)
