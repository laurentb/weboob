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

from urllib import unquote
import requests
import re
import sys
from copy import deepcopy
from cStringIO import StringIO
import lxml.html as html
import lxml.etree as etree

from weboob.tools.json import json
from weboob.tools.ordereddict import OrderedDict
from weboob.tools.regex_helper import normalize

from weboob.tools.log import getLogger

from .browser import DomainBrowser
from .filters import _Filter, CleanText, AttributeNotFound, XPathNotFound


class UrlNotResolvable(Exception):
    """
    Raised when trying to locate on an URL instance which url pattern is not resolvable as a real url.
    """


class DataError(Exception):
    """
    Returned data from pages are incoherent.
    """


class URL(object):
    """
    A description of an URL on the PagesBrowser website.

    It takes one or several regexps to match urls, and an optional BasePage
    class which is instancied by PagesBrowser.open if the page matches a regex.
    """
    _creation_counter = 0

    def __init__(self, *args):
        self.urls = []
        self.klass = None
        self.browser = None
        for arg in args:
            if isinstance(arg, basestring):
                self.urls.append(arg)
            if isinstance(arg, type):
                self.klass = arg

        self._creation_counter = URL._creation_counter
        URL._creation_counter += 1

    def is_here(self, **kwargs):
        """
        Returns True if the current page of browser matches this URL.
        If arguments are provided, and only then, they are checked against the arguments
        that were used to build the current page URL.
        """
        assert self.klass is not None, "You can use this method only if the is a BasePage class handler."

        if len(kwargs):
            params = self.match(self.build(**kwargs)).groupdict()
        else:
            params = None

        # XXX use unquote on current params values because if there are spaces
        # or special characters in them, it is encoded only in but not in kwargs.
        return self.browser.page and isinstance(self.browser.page, self.klass) \
            and (params is None or params == dict([(k,unquote(v)) for k,v in self.browser.page.params.iteritems()]))

    def stay_or_go(self, **kwargs):
        """
        Request to go on this url only if we aren't already here.

        Arguments are optional parameters for url.

        >>> url = URL('http://exawple.org/(?P<pagename>).html')
        >>> url.stay_or_go(pagename='index')
        """
        if self.is_here(**kwargs):
            return self.browser.page

        return self.go(**kwargs)

    def go(self, params=None, data=None, **kwargs):
        """
        Request to go on this url.

        Arguments are optional parameters for url.

        >>> url = URL('http://exawple.org/(?P<pagename>).html')
        >>> url.stay_or_go(pagename='index')
        """
        r = self.browser.location(self.build(**kwargs), params=params, data=data)
        return r.page or r

    def open(self, params=None, data=None, **kwargs):
        """
        Request to open on this url.

        Arguments are optional parameters for url.

        :param data: POST data
        :type url: str or dict or None

        >>> url = URL('http://exawple.org/(?P<pagename>).html')
        >>> url.open(pagename='index')
        """
        r = self.browser.open(self.build(**kwargs), params=params, data=data)
        return r.page or r

    def build(self, **kwargs):
        """
        Build an url with the given arguments from URL's regexps.

        :rtype: :class:`str`
        :raises: :class:`UrlNotResolvable` if unable to resolve a correct url with the given arguments.
        """
        patterns = []
        for url in self.urls:
            patterns += normalize(url)

        for pattern, _ in patterns:
            try:
                url = pattern % kwargs
            except KeyError:
                continue

            return self.browser.absurl(url, base=True)

        raise UrlNotResolvable('Unable to resolve URL with %r. Available are %s' % (kwargs, ', '.join([pattern for pattern, _ in patterns])))

    def match(self, url, base=None):
        """
        Check if the given url match this object.
        """
        if base is None:
            assert self.browser is not None
            base = self.browser.BASEURL

        for regex in self.urls:
            if regex.startswith('/'):
                regex = re.escape(base) + regex
            m = re.match(regex, url)
            if m:
                return m

    def handle(self, response):
        """
        Handle a HTTP response to get an instance of the klass if it matches.
        """
        if self.klass is None:
            return

        m = self.match(response.url)
        if m:
            return self.klass(self.browser, response, m.groupdict())

    def id2url(self, func):
        r"""
        Helper decorator to get an URL if the given first parameter is an ID.
        """
        def inner(browser, id_or_url, *args, **kwargs):
            if re.match('^https?://.*', id_or_url):
                if not self.match(id_or_url, browser.BASEURL):
                    return
            else:
                id_or_url = self.build(id=id_or_url)

            return func(browser, id_or_url, *args, **kwargs)
        return inner


class _PagesBrowserMeta(type):
    """
    Private meta-class used to keep order of URLs instances of PagesBrowser.
    """
    def __new__(mcs, name, bases, attrs):
        urls = [(url_name, attrs.pop(url_name)) for url_name, obj in attrs.items() if isinstance(obj, URL)]
        urls.sort(key=lambda x: x[1]._creation_counter)

        new_class = super(_PagesBrowserMeta, mcs).__new__(mcs, name, bases, attrs)
        if new_class._urls is None:
            new_class._urls = OrderedDict()
        else:
            new_class._urls = deepcopy(new_class._urls)
        new_class._urls.update(urls)
        return new_class

class PagesBrowser(DomainBrowser):
    r"""
    A browser which works pages and keep state of navigation.

    To use it, you have to derive it and to create URL objects as class
    attributes. When open() or location() are called, if the url matches
    one of URL objects, it returns a BasePage object. In case of location(), it
    stores it in self.page.

    Example:

    >>> class HomePage(BasePage):
    ...     pass
    ...
    >>> class ListPage(BasePage):
    ...     pass
    ...
    >>> class MyBrowser(PagesBrowser):
    ...     BASEURL = 'http://example.org'
    ...     home = URL('/(index\.html)?', HomePage)
    ...     list = URL('/list\.html', ListPage)
    ...

    You can then use URL instances to go on pages.
    """


    _urls = None
    __metaclass__ = _PagesBrowserMeta

    def __getattr__(self, name):
        if self._urls is not None and name in self._urls:
            return self._urls[name]
        else:
            raise AttributeError("'%s' object has no attribute '%s'" % (
                self.__class__.__name__, name))

    def __init__(self, *args, **kwargs):
        super(PagesBrowser, self).__init__(*args, **kwargs)

        self.page = None
        self._urls = deepcopy(self._urls)
        for url in self._urls.itervalues():
            url.browser = self

    def open(self, *args, **kwargs):
        """
        Same method than
        :meth:`weboob.tools.browser2.browser.DomainBrowser.open`, but the
        response contains an attribute `page` if the url matches any
        :class:`URL` object.
        """
        response = super(PagesBrowser, self).open(*args, **kwargs)
        response.page = None

        # Try to handle the response page with an URL instance.
        for url in self._urls.itervalues():
            page = url.handle(response)
            if page is not None:
                self.logger.debug('Handle %s with %s' % (response.url, page.__class__.__name__))
                response.page = page
                break

        if response.page is None:
            self.logger.debug('Unable to handle %s' % response.url)
        return response

    def location(self, *args, **kwargs):
        """
        Same method than
        :meth:`weboob.tools.browser2.browser.BaseBrowser.location`, but if the
        url matches any :class:`URL` object, an attribute `page` is added to
        response, and the attribute :attr:`PagesBrowser.page` is set.
        """
        if self.page is not None:
            # Call leave hook.
            self.page.on_leave()

        response = self.open(*args, **kwargs)

        self.response = response
        self.page = response.page
        self.url = response.url

        if self.page is not None:
            # Call load hook.
            self.page.on_load()

        # Returns self.response in case on_load recalls location()
        return self.response

    def pagination(self, func, *args, **kwargs):
        r"""
        This helper function can be used to handle pagination pages easily.

        When the called function raises an exception :class:`NextPage`, it goes
        on the wanted page and recall the function.

        :class:`NextPage` constructor can take an url or a Request object.

        >>> class Page(HTMLPage):
        ...     def iter_values(self):
        ...         for el in self.doc.xpath('//li'):
        ...             yield el.text
        ...         for next in self.doc.xpath('//a'):
        ...             raise NextPage(next.attrib['href'])
        ...
        >>> class Browser(PagesBrowser):
        ...     BASEURL = 'http://people.symlink.me'
        ...     list = URL('/~rom1/projects/weboob/list-(?P<pagenum>\d+).html', Page)
        ...
        >>> b = Browser()
        >>> b.list.go(pagenum=1)
        >>> list(b.pagination(lambda: b.page.iter_values()))
        ['One', 'Two', 'Three', 'Four']
        """
        while True:
            try:
                for r in func(*args, **kwargs):
                    yield r
            except NextPage as e:
                self.location(e.request)
            else:
                return

def pagination(func):
    r"""
    This helper decorator can be used to handle pagination pages easily.

    When the called function raises an exception :class:`NextPage`, it goes on
    the wanted page and recall the function.

    :class:`NextPage` constructor can take an url or a Request object.

    >>> class Page(HTMLPage):
    ...     @pagination
    ...     def iter_values(self):
    ...         for el in self.doc.xpath('//li'):
    ...             yield el.text
    ...         for next in self.doc.xpath('//a'):
    ...             raise NextPage(next.attrib['href'])
    ...
    >>> class Browser(PagesBrowser):
    ...     BASEURL = 'http://people.symlink.me'
    ...     list = URL('/~rom1/projects/weboob/list-(?P<pagenum>\d+).html', Page)
    ...
    >>> b = Browser()
    >>> b.list.go(pagenum=1)
    >>> list(b.page.iter_values())
    ['One', 'Two', 'Three', 'Four']
    """
    def inner(page, *args, **kwargs):
        while 1:
            try:
                for r in func(page, *args, **kwargs):
                    yield r
            except NextPage as e:
                result = page.browser.location(e.request)
                page = result.page
            else:
                return

    return inner

class NextPage(Exception):
    """
    Exception used for example in a BasePage to tell PagesBrowser.pagination to
    go on the next page.

    See :meth:`PagesBrowser.pagination` or decorator :func:`pagination`.
    """
    def __init__(self, request):
        super(NextPage, self).__init__()
        self.request = request


def need_login(func):
    """
    Decorator used to require to be logged to access to this function.
    """
    def inner(browser, *args, **kwargs):
        if browser.page is None or not browser.page.logged:
            browser.do_login()
        return func(browser, *args, **kwargs)

    return inner


class LoginBrowser(PagesBrowser):
    """
    A browser which supports login.
    """
    def __init__(self, username, password, *args, **kwargs):
        super(LoginBrowser, self).__init__(*args, **kwargs)
        self.username = username
        self.password = password

    def do_login(self):
        """
        Abstract method to implement to login on website.

        It is call when a login is needed.
        """
        raise NotImplementedError()


class BasePage(object):
    """
    Base page.
    """
    logged = False

    def __init__(self, browser, response, params):
        self.browser = browser
        self.logger = getLogger(self.__class__.__name__.lower(), browser.logger)
        self.response = response
        self.url = self.response.url
        self.params = params

    def on_load(self):
        """
        Event called when browser loads this page.
        """

    def on_leave(self):
        """
        Event called when browser leaves this page.
        """

class FormNotFound(Exception):
    """
    Raised when :meth:`HTMLPage.get_form` can't find a form.
    """

class Form(OrderedDict):
    """
    Represents a form of an HTML page.

    It is used as a dict with pre-filled values from HTML. You can set new
    values as strings by setting an item value.
    """

    def __init__(self, page, el):
        super(Form, self).__init__()
        self.page = page
        self.el = el
        self.method = el.attrib.get('method', 'GET')
        self.url = el.attrib.get('action', page.url)
        self.name = el.attrib.get('name', '')

        for inp in el.xpath('.//input | .//select | .//textarea'):
            try:
                name = inp.attrib['name']
            except KeyError:
                continue

            try:
                if inp.attrib['type'] in ('checkbox', 'radio') and not 'checked' in inp.attrib:
                    continue
            except KeyError:
                pass

            if inp.tag == 'select':
                options = inp.xpath('.//option[@selected]')
                if len(options) == 0:
                    options = inp.xpath('.//option')
                if len(options) == 0:
                    value = u''
                else:
                    value = options[0].attrib.get('value', options[0].text or u'')
            else:
                value = inp.attrib.get('value', inp.text or u'')
            self[name] = value

    @property
    def request(self):
        """
        Get the Request object from the form.
        """
        req = requests.Request(self.method, self.url, data=self)
        req.headers.setdefault('Referer', self.page.url)
        return req

    def submit(self):
        """
        Submit the form and tell browser to be located to the new page.
        """
        return self.page.browser.location(self.request)


class JsonPage(BasePage):
    def __init__(self, browser, response, *args, **kwargs):
        super(JsonPage, self).__init__(browser, response, *args, **kwargs)
        self.doc = json.loads(response.text)


class XMLPage(BasePage):
    def __init__(self, browser, response, *args, **kwargs):
        super(XMLPage, self).__init__(browser, response, *args, **kwargs)
        parser = etree.XMLParser(encoding=response.encoding)
        self.doc = etree.parse(StringIO(response.content), parser)


class RawPage(BasePage):
    def __init__(self, browser, response, *args, **kwargs):
        super(RawPage, self).__init__(browser, response, *args, **kwargs)
        self.doc = response.content


class HTMLPage(BasePage):
    """
    HTML page.
    """
    FORM_CLASS = Form

    def __init__(self, browser, response, *args, **kwargs):
        super(HTMLPage, self).__init__(browser, response, *args, **kwargs)
        parser = html.HTMLParser(encoding=response.encoding)
        self.doc = html.parse(StringIO(response.content), parser)

    def get_form(self, xpath='//form', name=None, nr=None):
        """
        Get a :class:`Form` object from a selector.

        :param xpath: xpath string to select forms
        :type xpath: :class:`str`
        :param name: if supplied, select a form with the given name
        :type name: :class:`str`
        :param nr: if supplied, take the n-th selected form
        :type nr: :class:`int`
        :rtype: :class:`Form`
        :raises: :class:`FormNotFound` if no form is found
        """
        i = 0
        for el in self.doc.xpath(xpath):
            if name is not None and el.attrib.get('name', '') != name:
                continue
            if nr is not None and i != nr:
                i += 1
                continue

            return self.FORM_CLASS(self, el)

        raise FormNotFound()


def method(klass):
    """
    Class-decorator to call it as a method.
    """
    def inner(self, *args, **kwargs):
        return klass(self)(*args, **kwargs)
    return inner


class AbstractElement(object):
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

    def use_selector(self, func):
        if isinstance(func, _Filter):
            value = func(self)
        elif callable(func):
            value = func()
        else:
            value = deepcopy(func)

        return value

    def parse(self, obj):
        pass

    def xpath(self, *args, **kwargs):
        return self.el.xpath(*args, **kwargs)


class ListElement(AbstractElement):
    item_xpath = None
    flush_at_end = False

    def __init__(self, *args, **kwargs):
        super(ListElement, self).__init__(*args, **kwargs)

        self.objects = {}

    def __call__(self, *args, **kwargs):
        for key, value in kwargs.iteritems():
            self.env[key] = value

        return self.__iter__()

    def __iter__(self):
        self.parse(self.el)

        if self.item_xpath is not None:
            for el in self.el.xpath(self.item_xpath):
                for obj in self.handle_element(el):
                    if not self.flush_at_end:
                        yield obj
        else:
            for obj in self.handle_element(self.el):
                if not self.flush_at_end:
                    yield obj

        if self.flush_at_end:
            for obj in self.objects.itervalues():
                yield obj

        self.check_next_page()

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
                raise DataError('There are two objects with the same ID! %s' % obj.id)
            self.objects[obj.id] = obj
        return obj

    def handle_element(self, el):
        for attrname in dir(self):
            attr = getattr(self, attrname)
            if isinstance(attr, type) and issubclass(attr, AbstractElement) and attr != type(self):
                for obj in attr(self.page, self, el):
                    yield self.store(obj)


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
        filters.sort(key=lambda x: x[1]._creation_counter if hasattr(x[1], '_creation_counter') else (sys.maxint if callable(x[1]) else 0))

        new_class = super(_ItemElementMeta, mcs).__new__(mcs, name, bases, attrs)
        new_class._attrs = _attrs + [f[0] for f in filters]
        return new_class


class ItemElement(AbstractElement):
    __metaclass__ = _ItemElementMeta

    _attrs = None
    klass = None
    condition = None
    validate = None

    class Index(object):
        pass

    def __init__(self, *args, **kwargs):
        super(ItemElement, self).__init__(*args, **kwargs)
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
            for attr in self._attrs:
                self.handle_attr(attr, getattr(self, 'obj_%s' % attr))
        except SkipItem:
            return

        if self.validate is not None and not self.validate(self.obj):
            return

        yield self.obj

    def handle_attr(self, key, func):
        value = self.use_selector(func)
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
                columns[m.group(1)] = [s.lower() for s in cols]

        for colnum, el in enumerate(self.el.xpath(self.head_xpath)):
            title = self.cleaner.clean(el).lower()
            for name, titles in columns.iteritems():
                if title in titles:
                    self._cols[name] = colnum

    def get_colnum(self, name):
        return self._cols.get(name, None)


class LoggedPage(object):
    """
    A page that only logged users can reach. If we did not get a redirection
    for this page, we are sure that the login is still active.

    Do not use this class for page we mixed content (logged/anonymous) or for
    pages with a login form.
    """
    logged = True
