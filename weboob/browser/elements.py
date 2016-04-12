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

import re
import sys
from copy import deepcopy

from weboob.tools.log import getLogger, DEBUG_FILTERS
from weboob.tools.ordereddict import OrderedDict
from weboob.browser.pages import NextPage

from .filters.standard import _Filter, CleanText
from .filters.html import AttributeNotFound, XPathNotFound


__all__ = ['DataError', 'AbstractElement', 'ListElement', 'ItemElement', 'TableElement', 'SkipItem']


class DataError(Exception):
    """
    Returned data from pages are incoherent.
    """


def method(klass):
    """
    Class-decorator to call it as a method.
    """

    def inner(self, *args, **kwargs):
        return klass(self)(*args, **kwargs)
    return inner


class AbstractElement(object):
    _creation_counter = 0

    def __init__(self, page, parent=None, el=None):
        self.page = page
        self.parent = parent
        if el is not None:
            self.el = el
        elif parent is not None:
            self.el = parent.el
        else:
            self.el = page.doc

        if parent is not None:
            self.env = deepcopy(parent.env)
        else:
            self.env = deepcopy(page.params)

        # Used by debug
        self._random_id = AbstractElement._creation_counter
        AbstractElement._creation_counter += 1

        self.loaders = {}

    def use_selector(self, func, key=None):
        if isinstance(func, _Filter):
            func._obj = self
            func._key = key
            value = func(self)
        elif isinstance(func, type) and issubclass(func, ItemElement):
            value = func(self.page, self, self.el)()
        elif callable(func):
            value = func()
        else:
            value = deepcopy(func)

        return value

    def parse(self, obj):
        pass

    def cssselect(self, *args, **kwargs):
        return self.el.cssselect(*args, **kwargs)

    def xpath(self, *args, **kwargs):
        return self.el.xpath(*args, **kwargs)

    def handle_loaders(self):
        for attrname in dir(self):
            m = re.match('load_(.*)', attrname)
            if not m:
                continue
            name = m.group(1)
            if name in self.loaders:
                continue
            loader = getattr(self, attrname)
            self.loaders[name] = self.use_selector(loader, key=attrname)


class ListElement(AbstractElement):
    item_xpath = None
    flush_at_end = False
    ignore_duplicate = False

    def __init__(self, *args, **kwargs):
        super(ListElement, self).__init__(*args, **kwargs)
        self.logger = getLogger(self.__class__.__name__.lower())
        self.objects = OrderedDict()

    def __call__(self, *args, **kwargs):
        for key, value in kwargs.iteritems():
            self.env[key] = value

        return self.__iter__()

    def find_elements(self):
        """
        Get the nodes that will have to be processed.
        This method can be overridden if xpath filters are not
        sufficient.
        """
        if self.item_xpath is not None:
            for el in self.el.xpath(self.item_xpath):
                yield el
        else:
            yield self.el

    def __iter__(self):
        self.parse(self.el)

        items = []
        for el in self.find_elements():
            for attrname in dir(self):
                attr = getattr(self, attrname)
                if isinstance(attr, type) and issubclass(attr, AbstractElement) and attr != type(self):
                    item = attr(self.page, self, el)
                    item.handle_loaders()
                    items.append(item)

        for item in items:
            for obj in item:
                obj = self.store(obj)
                if obj and not self.flush_at_end:
                    yield obj

        if self.flush_at_end:
            for obj in self.flush():
                yield obj

        self.check_next_page()

    def flush(self):
        for obj in self.objects.itervalues():
            yield obj

    def check_next_page(self):
        if not hasattr(self, 'next_page'):
            return

        next_page = getattr(self, 'next_page')
        try:
            value = self.use_selector(next_page)
        except (AttributeNotFound, XPathNotFound):
            return

        if value is None:
            return

        raise NextPage(value)


    def store(self, obj):
        if obj.id:
            if obj.id in self.objects:
                if self.ignore_duplicate:
                    self.logger.warning('There are two objects with the same ID! %s' % obj.id)
                    return
                else:
                    raise DataError('There are two objects with the same ID! %s' % obj.id)
            self.objects[obj.id] = obj
        return obj


class SkipItem(Exception):
    """
    Raise this exception in an :class:`ItemElement` subclass to skip an item.
    """


class _ItemElementMeta(type):
    """
    Private meta-class used to keep order of obj_* attributes in :class:`ItemElement`.
    """
    def __new__(mcs, name, bases, attrs):
        _attrs = []
        for base in bases:
            if hasattr(base, '_attrs'):
                _attrs += base._attrs

        filters = [(re.sub('^obj_', '', attr_name), attrs[attr_name]) for attr_name, obj in attrs.items() if attr_name.startswith('obj_')]
        # constants first, then filters, then methods
        filters.sort(key=lambda x: x[1]._creation_counter if hasattr(x[1], '_creation_counter') else (sys.maxsize if callable(x[1]) else 0))

        new_class = super(_ItemElementMeta, mcs).__new__(mcs, name, bases, attrs)
        new_class._attrs = _attrs + [f[0] for f in filters]
        return new_class


class ItemElement(AbstractElement):
    __metaclass__ = _ItemElementMeta

    _attrs = None
    _loaders = None
    klass = None
    condition = None
    validate = None

    class Index(object):
        pass

    def __init__(self, *args, **kwargs):
        super(ItemElement, self).__init__(*args, **kwargs)
        self.logger = getLogger(self.__class__.__name__.lower())
        self.obj = None

    def build_object(self):
        if self.klass is None:
            return
        return self.klass()

    def __call__(self, obj=None):
        if obj is not None:
            self.obj = obj

        for obj in self:
            return obj

    def __iter__(self):
        if self.condition is not None and not self.condition():
            return

        try:
            if self.obj is None:
                self.obj = self.build_object()
            self.parse(self.el)
            self.handle_loaders()
            for attr in self._attrs:
                self.handle_attr(attr, getattr(self, 'obj_%s' % attr))
        except SkipItem:
            return

        if self.validate is not None and not self.validate(self.obj):
            return

        yield self.obj

    def handle_attr(self, key, func):
        try:
            value = self.use_selector(func, key=key)
        except Exception as e:
            # Help debugging as tracebacks do not give us the key
            self.logger.warning('Attribute %s raises %s' % (key, repr(e)))
            raise
        logger = getLogger('b2filters')
        logger.log(DEBUG_FILTERS, "%s.%s = %r" % (self._random_id, key, value))
        setattr(self.obj, key, value)


class TableElement(ListElement):
    head_xpath = None
    cleaner = CleanText

    def __init__(self, *args, **kwargs):
        super(TableElement, self).__init__(*args, **kwargs)

        self._cols = {}

        columns = {}
        for attrname in dir(self):
            m = re.match('col_(.*)', attrname)
            if m:
                cols = getattr(self, attrname)
                if not isinstance(cols, (list,tuple)):
                    cols = [cols]
                columns[m.group(1)] = [s.lower() if isinstance(s, (str, unicode)) else s for s in cols]

        colnum = 0
        for el in self.el.xpath(self.head_xpath):
            title = self.cleaner.clean(el)
            for name, titles in columns.iteritems():
                if name in self._cols:
                    continue
                if title.lower() in [s for s in titles if isinstance(s, (str, unicode))] or \
                   any(map(lambda x: x.match(title), [s for s in titles if isinstance(s, type(re.compile('')))])):
                    self._cols[name] = colnum
            try:
                colnum += int(el.attrib.get('colspan', 1))
            except (ValueError, AttributeError):
                colnum += 1

    def get_colnum(self, name):
        return self._cols.get(name, None)


class DictElement(ListElement):
    def find_elements(self):
        if self.item_xpath is None:
            selector = []

        elif isinstance(self.item_xpath, basestring):
            selector = self.item_xpath.split('/')

        else:
            selector = self.item_xpath

        _subdict = False
        for el in selector:
            if isinstance(self.el, list):
                if _subdict:
                    subdicts = []
                    for i in range (0, len(self.el)):
                        _el = int(el) if isinstance(self.el[i], list) else el
                        subdicts += self.el[i][_el]
                    self.el = subdicts
                    _subdict = False
                    continue

                if el == '*':
                    _subdict = True
                    continue
                elif el.isdigit():
                    el = int(el) if int(el) < len(self.el) else 0

            self.el = self.el[el]

        for el in self.el:
            yield el
