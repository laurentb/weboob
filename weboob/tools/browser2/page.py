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

try:
    from urllib.parse import unquote
except ImportError:
    from urllib import unquote
import re
from copy import deepcopy
from io import BytesIO

import requests

from weboob.tools.ordereddict import OrderedDict
from weboob.tools.regex_helper import normalize
from weboob.tools.compat import basestring

from weboob.tools.log import getLogger

from .browser import DomainBrowser


class UrlNotResolvable(Exception):
    """
    Raised when trying to locate on an URL instance which url pattern is not resolvable as a real url.
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

        :param param: Query string parameters

        :rtype: :class:`str`
        :raises: :class:`UrlNotResolvable` if unable to resolve a correct url with the given arguments.
        """
        browser = kwargs.pop('browser', self.browser)
        params = kwargs.pop('params', None)
        patterns = []
        for url in self.urls:
            patterns += normalize(url)

        for pattern, _ in patterns:
            url = pattern
            # only use full-name substitutions, to allow % in URLs
            for kwkey in kwargs.keys():  # need to use keys() because of pop()
                search = '%%(%s)s' % kwkey
                if search in pattern:
                    url = url.replace(search, unicode(kwargs.pop(kwkey)))
            # if there are named substitutions left, ignore pattern
            if re.search('%\([A-z_]+\)s', url):
                continue
            # if not all kwargs were used
            if len(kwargs):
                continue

            url = browser.absurl(url, base=True)
            if params:
                p = requests.models.PreparedRequest()
                p.prepare_url(url, params)
                url = p.url
            return url

        raise UrlNotResolvable('Unable to resolve URL with %r. Available are %s' % (kwargs, ', '.join([pattern for pattern, _ in patterns])))

    def match(self, url, base=None):
        """
        Check if the given url match this object.
        """
        if base is None:
            assert self.browser is not None
            base = self.browser.BASEURL

        for regex in self.urls:
            if not re.match(r'^\w+://.*', regex):
                regex = re.escape(base).rstrip('/') + '/' + regex.lstrip('/')
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
            page = self.klass(self.browser, response, m.groupdict())
            if hasattr(page, 'is_here'):
                if callable(page.is_here):
                    if page.is_here():
                        return page
                else:
                    assert isinstance(page.is_here, basestring)
                    if page.doc.xpath(page.is_here):
                        return page
            else:
                return page

    def id2url(self, func):
        r"""
        Helper decorator to get an URL if the given first parameter is an ID.
        """
        def inner(browser, id_or_url, *args, **kwargs):
            if re.match('^https?://.*', id_or_url):
                if not self.match(id_or_url, browser.BASEURL):
                    return
            else:
                id_or_url = self.build(id=id_or_url, browser=browser)

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
        while True:
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

    def __init__(self, browser, response, params=None):
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
                if inp.attrib['type'] in ('checkbox', 'radio') and 'checked' not in inp.attrib:
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
        if self.method.lower() == 'get':
            req = requests.Request(self.method, self.url, params=self)
        else:
            req = requests.Request(self.method, self.url, data=self)
        req.headers.setdefault('Referer', self.page.url)
        return req

    def submit(self, **kwargs):
        """
        Submit the form and tell browser to be located to the new page.
        """
        kwargs.setdefault('data_encoding', self.page.encoding)
        return self.page.browser.location(self.request, **kwargs)


class CsvPage(BasePage):
    DIALECT = 'excel'
    FMTPARAMS = {}
    ENCODING = 'utf-8'
    NEWLINES_HACK = True

    """
    If True, will consider the first line as a header.
    This means the rows will be also available as dictionnaries.
    """
    HEADER = None

    def __init__(self, browser, response, *args, **kwargs):
        super(CsvPage, self).__init__(browser, response, *args, **kwargs)
        content = response.content
        encoding = self.ENCODING
        if encoding == 'utf-16le':
            content = content.decode('utf-16le')[1:].encode('utf-8')
            encoding = 'utf-8'
        if self.NEWLINES_HACK:
            content = content.replace('\r\n', '\n').replace('\r', '\n')
        fp = BytesIO(content)
        self.doc = self.parse(fp, encoding)

    def parse(self, data, encoding=None):
        import csv
        reader = csv.reader(data, dialect=self.DIALECT, **self.FMTPARAMS)
        header = None
        drows = []
        rows = []
        for i, row in enumerate(reader):
            if self.HEADER and i+1 < self.HEADER:
                continue
            row = self.decode_row(row, encoding)
            if header is None and self.HEADER:
                header = row
            else:
                rows.append(row)
                if header:
                    drow = {}
                    for i, cell in enumerate(row):
                        drow[header[i]] = cell
                    drows.append(drow)
        return drows if header is not None else row

    def decode_row(self, row, encoding):
        if encoding:
            return [unicode(cell, encoding) for cell in row]
        else:
            return row


class JsonPage(BasePage):
    def __init__(self, browser, response, *args, **kwargs):
        super(JsonPage, self).__init__(browser, response, *args, **kwargs)
        from weboob.tools.json import json
        self.doc = json.loads(response.text)


class XMLPage(BasePage):
    ENCODING = None
    """
    Force a page encoding.
    It is recommended to use None for autodetection.
    """

    def __init__(self, browser, response, *args, **kwargs):
        super(XMLPage, self).__init__(browser, response, *args, **kwargs)
        import lxml.etree as etree
        parser = etree.XMLParser(encoding=self.ENCODING or response.encoding)
        self.doc = etree.parse(BytesIO(response.content), parser)


class RawPage(BasePage):
    def __init__(self, browser, response, *args, **kwargs):
        super(RawPage, self).__init__(browser, response, *args, **kwargs)
        self.doc = response.content


class HTMLPage(BasePage):
    """
    HTML page.
    """
    FORM_CLASS = Form

    ENCODING = None
    """
    Force a page encoding.
    It is recommended to use None for autodetection.
    """

    def __init__(self, browser, response, *args, **kwargs):
        super(HTMLPage, self).__init__(browser, response, *args, **kwargs)
        self.encoding = self.ENCODING or response.encoding
        import lxml.html as html
        parser = html.HTMLParser(encoding=self.encoding)
        self.doc = html.parse(BytesIO(response.content), parser)

    def get_form(self, xpath='//form', name=None, nr=None):
        """
        Get a :class:`Form` object from a selector.

        :param xpath: xpath string to select forms
        :type xpath: :class:`str`
        :param name: if supplied, select a form with the given name
        :type name: :class:`str`
        :param nr: if supplied, take the n+1 th selected form
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


class LoggedPage(object):
    """
    A page that only logged users can reach. If we did not get a redirection
    for this page, we are sure that the login is still active.

    Do not use this class for page we mixed content (logged/anonymous) or for
    pages with a login form.
    """
    logged = True
