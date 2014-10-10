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

import warnings
from io import BytesIO
import codecs
from cgi import parse_header

import requests

from weboob.tools.ordereddict import OrderedDict
from weboob.tools.compat import basestring

from weboob.tools.log import getLogger


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
    >>> from .browsers import PagesBrowser
    >>> from .url import URL
    >>> class Browser(PagesBrowser):
    ...     BASEURL = 'http://people.symlink.me'
    ...     list = URL('/~rom1/projects/weboob/list-(?P<pagenum>\d+).html', Page)
    ...
    >>> b = Browser()
    >>> b.list.go(pagenum=1) # doctest: +ELLIPSIS
    <weboob.browser.pages.Page object at 0x...>
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
    Exception used for example in a Page to tell PagesBrowser.pagination to
    go on the next page.

    See :meth:`PagesBrowser.pagination` or decorator :func:`pagination`.
    """

    def __init__(self, request):
        super(NextPage, self).__init__()
        self.request = request


class Page(object):
    """
    Represents a page.

    :param browser: browser used to go on the page
    :type browser: :class:`weboob.browser.browsers.Browser`
    :param response: response object
    :type response: :class:`Response`
    :param params: optional dictionary containing parameters given to the page (see :class:`weboob.browser.url.URL`)
    :type params: :class:`dict`
    """

    logged = False
    """
    If True, the page is in a restrected area of the wesite. Useful with
    :class:`LoginBrowser` and the :func:`need_login` decorator.
    """

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


class FormSubmitWarning(UserWarning):
    """
    A form has more than one submit element selected, and will likely
    generate an invalid request.
    """


class Form(OrderedDict):
    """
    Represents a form of an HTML page.

    It is used as a dict with pre-filled values from HTML. You can set new
    values as strings by setting an item value.

    It is recommended to not use this class by yourself, but call
    :meth:`HTMLPage.get_form`.

    :param page: the page where the form is located
    :type page: :class:`Page`
    :param el: the form element on the page
    :param submit_el: allows you to only consider one submit button (which is
                      what browsers do). If set to None, it takes all of them,
                      and if set to False, it takes none.
    """

    def __init__(self, page, el, submit_el=None):
        super(Form, self).__init__()
        self.page = page
        self.el = el
        self.submit_el = submit_el
        self.method = el.attrib.get('method', 'GET')
        self.url = el.attrib.get('action', page.url)
        self.name = el.attrib.get('name', '')
        submits = 0

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

            try:
                if inp.attrib['type'] == 'submit':
                    if self.submit_el is not None and inp is not self.submit_el:
                        continue
                    else:
                        submits += 1
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

        if submits > 1:
            warnings.warn('Form has more than one submit input, you should chose the correct one', FormSubmitWarning, stacklevel=3)
        if self.submit_el is not None and self.submit_el is not False and submits == 0:
            warnings.warn('Form had a submit element provided, but it was not found', FormSubmitWarning, stacklevel=3)


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


class CsvPage(Page):
    """
    Page which parses CSV files.
    """

    DIALECT = 'excel'
    """
    Dialect given to the :mod:`csv` module.
    """

    FMTPARAMS = {}
    """
    Parameters given to the :mod:`csv` module.
    """

    ENCODING = 'utf-8'
    """
    Encoding of the file.
    """

    NEWLINES_HACK = True
    """
    Convert all strange newlines to unix ones.
    """

    HEADER = None
    """
    If not None, will consider the line represented by this index as a header.
    This means the rows will be also available as dictionaries.
    """

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
        """
        Method called by the constructor of :class:`CsvPage` to parse the document.

        :param data: file stream
        :type data: :class:`BytesIO`
        :param encoding: if given, use it to decode cell strings
        :type encoding: :class:`str`
        """
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
        return drows if header is not None else rows

    def decode_row(self, row, encoding):
        """
        Method called by :meth:`CsvPage.parse` to decode a row using the given encoding.
        """
        if encoding:
            return [unicode(cell, encoding) for cell in row]
        else:
            return row


class JsonPage(Page):
    """
    Json Page.
    """

    def __init__(self, browser, response, *args, **kwargs):
        super(JsonPage, self).__init__(browser, response, *args, **kwargs)
        from weboob.tools.json import json
        self.doc = json.loads(response.text)


class XMLPage(Page):
    """
    XML Page.
    """

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


class RawPage(Page):
    """
    Raw page where the "doc" attribute is the content string.
    """

    def __init__(self, browser, response, *args, **kwargs):
        super(RawPage, self).__init__(browser, response, *args, **kwargs)
        self.doc = response.content


class HTMLPage(Page):
    """
    HTML page.

    :param browser: browser used to go on the page
    :type browser: :class:`weboob.browser.browsers.Browser`
    :param response: response object
    :type response: :class:`Response`
    :param params: optional dictionary containing parameters given to the page (see :class:`weboob.browser.url.URL`)
    :type params: :class:`dict`
    :param encoding: optional parameter to force the encoding of the page
    :type encoding: :class:`basestring`

    """

    FORM_CLASS = Form
    """
    The class to instanciate when using :meth:`HTMLPage.get_form`. Default to :class:`Form`.
    """

    ENCODING = None
    """
    Force a page encoding.
    It is recommended to use None for autodetection.
    """

    def __init__(self, *args, **kwargs):
        encoding = kwargs.pop('encoding', self.ENCODING)

        super(HTMLPage, self).__init__(*args, **kwargs)
        self.doc = None
        self.encoding = None

        import lxml.html as html
        ns = html.etree.FunctionNamespace(None)
        self.define_xpath_functions(ns)
        self.build_doc(encoding)
        if encoding is None:
            self.check_encoding()

    def define_xpath_functions(self, ns):
        """
        Define XPath functions on the given lxml function namespace.

        This method is called in constructor of :class:`HTMLPage` and can be
        overloaded by children classes to add extra functions.
        """
        ns['lower-case'] = lambda context, args: ' '.join([s.lower() for s in args])

        def has_class(context, *classes):
            """
            This lxml extension allows to select by CSS class more easily

            >>> ns = html.etree.FunctionNamespace(None)
            >>> ns['has-class'] = has_class
            >>> root = html.etree.fromstring('''
            ... <a>
            ...     <b class="one first text">I</b>
            ...     <b class="two text">LOVE</b>
            ...     <b class="three text">CSS</b>
            ... </a>
            ... ''')

            >>> len(root.xpath('//b[has-class("text")]'))
            3
            >>> len(root.xpath('//b[has-class("one")]'))
            1
            >>> len(root.xpath('//b[has-class("text", "first")]'))
            1
            >>> len(root.xpath('//b[not(has-class("first"))]'))
            2
            >>> len(root.xpath('//b[has-class("not-exists")]'))
            0
            """
            expressions = ' and '.join(["contains(concat(' ', normalize-space(@class), ' '), ' {} ')".format(c) for c in classes])
            xpath = 'self::*[@class and {}]'.format(expressions)
            return bool(context.context_node.xpath(xpath))
        ns['has-class'] = has_class

    def build_doc(self, encoding=None):
        """
        Method to build the lxml document from response and given encoding.
        """
        if encoding is None:
            encoding = self.response.encoding

        import lxml.html as html
        parser = html.HTMLParser(encoding=encoding)
        self.doc = html.parse(BytesIO(self.response.content), parser)
        self.encoding = encoding
        return self.doc

    def check_encoding(self):
        """
        Check in the document the "http-equiv" and "charset" meta nodes. If the
        specified charset isn't the one given by Content-Type HTTP header,
        parse document again with the right encoding.
        """
        encoding = self.encoding
        for content in self.doc.xpath('//head/meta[lower-case(@http-equiv)="content-type"]/@content'):
            # meta http-equiv=content-type content=...
            _, params = parse_header(content)
            if 'charset' in params:
                encoding = params['charset'].strip("'\"")

        for charset in self.doc.xpath('//head/meta[@charset]/@charset'):
            # meta charset=...
            encoding = charset.lower()

        if encoding == 'iso-8859-1' or not encoding:
            encoding = 'windows-1252'
        try:
            codecs.lookup(encoding)
        except LookupError:
            encoding = 'windows-1252'

        if encoding != self.encoding:
            self.build_doc(encoding)

    def get_form(self, xpath='//form', name=None, nr=None, submit=None):
        """
        Get a :class:`Form` object from a selector.
        The form will be analyzed and its parameters extracted.
        In the case there is more than one "submit" input, only one of
        them should be chosen to generate the request.

        :param xpath: xpath string to select forms
        :type xpath: :class:`str`
        :param name: if supplied, select a form with the given name
        :type name: :class:`str`
        :param nr: if supplied, take the n+1 th selected form
        :type nr: :class:`int`
        :param submit: if supplied, xpath string to select the submit \
            element from the form
        :type submit: :class:`str`
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

            if isinstance(submit, basestring):
                submit_el = el.xpath(submit)[0]
            else:
                submit_el = submit

            return self.FORM_CLASS(self, el, submit_el)

        raise FormNotFound()


class LoggedPage(object):
    """
    A page that only logged users can reach. If we did not get a redirection
    for this page, we are sure that the login is still active.

    Do not use this class for page we mixed content (logged/anonymous) or for
    pages with a login form.
    """
    logged = True
