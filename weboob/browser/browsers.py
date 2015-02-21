# -*- coding: utf-8 -*-

# Copyright(C) 2012-2014 Laurent Bachelier
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

from __future__ import absolute_import, print_function

import re
import pickle
import base64
import zlib
try:
    import urllib3
except ImportError:
    from requests.packages import urllib3
try:
    from urllib.parse import urlparse, urljoin
except ImportError:
    from urlparse import urlparse, urljoin
import os
import sys
from copy import deepcopy
import inspect

try:
    import requests
    if int(requests.__version__.split('.')[0]) < 2:
        raise ImportError()
except ImportError:
    raise ImportError('Please install python-requests >= 2.0')

from weboob.tools.log import getLogger
from weboob.tools.ordereddict import OrderedDict
from weboob.tools.json import json

from .cookies import WeboobCookieJar
from .exceptions import HTTPNotFound, ClientError, ServerError
from .sessions import FuturesSession
from .profiles import Firefox
from .pages import NextPage
from .url import URL


class Browser(object):
    """
    Simple browser class.
    Act like a browser, and don't try to do too much.
    """

    PROFILE = Firefox()
    """
    Default profile used by browser to navigate on websites.
    """

    TIMEOUT = 10.0
    """
    Default timeout during requests.
    """

    REFRESH_MAX = 0.0
    """
    When handling a Refresh header, the browsers considers it only if the sleep
    time in lesser than this value.
    """

    VERIFY = True
    """
    Check SSL certificates.
    """

    PROXIES = None

    MAX_RETRIES = 2

    MAX_WORKERS = 10
    """
    Maximum of threads for asynchronous requests.
    """

    __states__ = []
    """
    Saved state variables.
    """

    @classmethod
    def asset(cls, localfile):
        """
        Absolute file path for a module local file.
        """
        if os.path.isabs(localfile):
            return localfile
        return os.path.join(os.path.dirname(inspect.getfile(cls)), localfile)

    def __init__(self, logger=None, proxy=None, responses_dirname=None):
        self.logger = getLogger('browser', logger)
        self.PROXIES = proxy
        self._setup_session(self.PROFILE)
        self.url = None
        self.response = None

        self.responses_dirname = responses_dirname
        self.responses_count = 1

        if isinstance(self.VERIFY, basestring):
            self.VERIFY = self.asset(self.VERIFY)

    def load_state(self, state):
        if 'cookies' in state:
            try:
                self.session.cookies = pickle.loads(zlib.decompress(base64.b64decode(state['cookies'])))
            except (TypeError, zlib.error, EOFError, ValueError):
                self.logger.error('Unable to reload cookies from storage')
            else:
                self.logger.info('Reloaded cookies from storage')
        for attrname in self.__states__:
            if attrname in state:
                setattr(self, attrname, state[attrname])

    def dump_state(self):
        state = {}
        state['cookies'] = base64.b64encode(zlib.compress(pickle.dumps(self.session.cookies, -1)))
        for attrname in self.__states__:
            state[attrname] = getattr(self, attrname)
        self.logger.info('Stored cookies into storage')
        return state

    def save_response(self, response, warning=False, **kwargs):
        if self.responses_dirname is None:
            import tempfile
            self.responses_dirname = tempfile.mkdtemp(prefix='weboob_session_')
            print('Debug data will be saved in this directory: %s' % self.responses_dirname, file=sys.stderr)
        elif not os.path.isdir(self.responses_dirname):
            os.makedirs(self.responses_dirname)

        import mimetypes
        # get the content-type, remove optionnal charset part
        mimetype = response.headers.get('Content-Type', '').split(';')[0]
        # due to http://bugs.python.org/issue1043134
        if mimetype == 'text/plain':
            ext = '.txt'
        else:
            # try to get an extension (and avoid adding 'None')
            ext = mimetypes.guess_extension(mimetype, False) or ''

        path = re.sub(r'[^A-z0-9\.-_]+', '_', urlparse(response.url).path.rpartition('/')[2])[-10:]
        if path.endswith(ext):
            ext = ''
        filename = '%02d-%d%s%s%s' % \
            (self.responses_count, response.status_code, '-' if path else '', path, ext)

        response_filepath = os.path.join(self.responses_dirname, filename)
        with open(response_filepath, 'w') as f:
            f.write(response.content)

        request = response.request
        with open(response_filepath + '-request.txt', 'w') as f:
            f.write('%s %s\n\n\n' % (request.method, request.url))
            for key, value in request.headers.iteritems():
                f.write('%s: %s\n' % (key, value))
            if request.body is not None:  # separate '' from None
                f.write('\n\n\n%s' % request.body)
        with open(response_filepath + '-response.txt', 'w') as f:
            if hasattr(response.elapsed, 'total_seconds'):
                f.write('Time: %3.3fs\n' % response.elapsed.total_seconds())
            f.write('%s %s\n\n\n' % (response.status_code, response.reason))
            for key, value in response.headers.iteritems():
                f.write('%s: %s\n' % (key, value))

        match_filepath = os.path.join(self.responses_dirname, 'url_response_match.txt')
        with open(match_filepath, 'a') as f:
            f.write('# %d %s %s\n' % (response.status_code, response.reason, response.headers.get('Content-Type', '')))
            f.write('%s\t%s\n' % (response.url, filename))
        self.responses_count += 1

        msg = u'Response saved to %s' % response_filepath
        if warning:
            self.logger.warning(msg)
        else:
            self.logger.info(msg)

    def _setup_session(self, profile):
        """
        Set up a python-requests session for our usage.
        """
        session = FuturesSession(max_workers=self.MAX_WORKERS)

        session.proxies = self.PROXIES

        session.verify = not self.logger.settings['ssl_insecure'] and self.VERIFY
        if not session.verify:
            try:
                urllib3.disable_warnings()
            except AttributeError:
                # urllib3 is too old, warnings won't be disable
                pass

        # defines a max_retries. It's mandatory in case a server is not
        # handling keep alive correctly, like the proxy burp
        a = requests.adapters.HTTPAdapter(max_retries=self.MAX_RETRIES)
        session.mount('http://', a)
        session.mount('https://', a)

        if self.TIMEOUT:
            session.timeout = self.TIMEOUT
        ## weboob only can provide proxy and HTTP auth options
        session.trust_env = False

        profile.setup_session(session)

        if self.logger.settings['save_responses']:
            session.hooks['response'].append(self.save_response)

        self.session = session

        session.cookies = WeboobCookieJar()

    def set_profile(self, profile):
        profile.setup_session(self.session)

    def location(self, url, **kwargs):
        """
        Like :meth:`open` but also changes the current URL and response.
        This is the most common method to request web pages.

        Other than that, has the exact same behavior of open().
        """
        assert not kwargs.get('async'), "Please use open() instead of location() to make asynchronous requests."
        response = self.open(url, **kwargs)
        self.response = response
        self.url = self.response.url
        return response

    def open(self, url, referrer=None,
                   allow_redirects=True,
                   stream=None,
                   timeout=None,
                   verify=None,
                   cert=None,
                   proxies=None,
                   data_encoding=None,
                   async=False,
                   callback=lambda response: response,
                   **kwargs):
        """
        Make an HTTP request like a browser does:
         * follow redirects (unless disabled)
         * provide referrers (unless disabled)

        Unless a `method` is explicitly provided, it makes a GET request,
        or a POST if data is not None,
        An empty `data` (not None, like '' or {}) *will* make a POST.

        It is a wrapper around session.request().
        All session.request() options are available.
        You should use location() or open() and not session.request(),
        since it has some interesting additions, which are easily
        individually disabled through the arguments.

        Call this instead of location() if you do not want to "visit" the URL
        (for instance, you are downloading a file).

        When `async` is True, open() returns a Future objet (see
        concurrent.futures for more details), which can be evaluated with its
        result() method. If any exception is raised while processing request,
        it is catched and re-raised when calling result().

        For example:

        >>> Browser().open('http://google.com', async=True).result().text # doctest: +SKIP

        :param url: URL
        :type url: str

        :param data: POST data
        :type url: str or dict or None

        :param referrer: Force referrer. False to disable sending it, None for guessing
        :type referrer: str or False or None

        :param async: Process request in a non-blocking way
        :type async: bool

        :param callback: Callback to be called when request has finished,
                         with response as its first and only argument
        :type callback: function

        :rtype: :class:`requests.Response`
        """
        req = self.build_request(url, referrer, data_encoding=data_encoding, **kwargs)
        preq = self.prepare_request(req)

        if hasattr(preq, '_cookies'):
            # The _cookies attribute is not present in requests < 2.2. As in
            # previous version it doesn't calls extract_cookies_to_jar(), it is
            # not a problem as we keep our own cookiejar instance.
            preq._cookies = WeboobCookieJar.from_cookiejar(preq._cookies)

        if proxies is None:
            proxies = self.PROXIES

        if verify is None:
            verify = not self.logger.settings['ssl_insecure'] and self.VERIFY

        if timeout is None:
            timeout = self.TIMEOUT

        # We define an inner_callback here in order to execute the same code
        # regardless of async param.
        def inner_callback(future, response):
            if allow_redirects:
                response = self.handle_refresh(response)

            self.raise_for_status(response)
            return callback(response)

        # call python-requests
        response = self.session.send(preq,
                                     allow_redirects=allow_redirects,
                                     stream=stream,
                                     timeout=timeout,
                                     verify=verify,
                                     cert=cert,
                                     proxies=proxies,
                                     background_callback=async and inner_callback)
        if not async:
            inner_callback(self, response)

        return response

    def async_open(self, url, **kwargs):
        """
        Shortcut to open(url, async=True).
        """
        if 'async' in kwargs:
            del kwargs['async']
        return self.open(url, async=True, **kwargs)

    def raise_for_status(self, response):
        """
        Like Response.raise_for_status but will use other classes if needed.
        """
        http_error_msg = None
        if 400 <= response.status_code < 500:
            http_error_msg = '%s Client Error: %s' % (response.status_code, response.reason)
            cls = ClientError
            if response.status_code == 404:
                cls = HTTPNotFound
        elif 500 <= response.status_code < 600:
            http_error_msg = '%s Server Error: %s' % (response.status_code, response.reason)
            cls = ServerError

        if http_error_msg:
            raise cls(http_error_msg, response=response)

        # in case we did not catch something that should be
        response.raise_for_status()


    def build_request(self, url, referrer=None, data_encoding=None, **kwargs):
        """
        Does the same job as open(), but returns a Request without
        submitting it.
        This allows further customization to the Request.
        """
        if isinstance(url, requests.Request):
            req = url
            url = req.url
        else:
            req = requests.Request(url=url, **kwargs)

        # guess method
        if req.method is None:
            if req.data:
                req.method = 'POST'
            else:
                req.method = 'GET'

        # convert unicode strings to proper encoding
        if isinstance(req.data, unicode) and data_encoding:
            req.data = req.data.encode(data_encoding)
        if isinstance(req.data, dict) and data_encoding:
            req.data = dict([(k, v.encode(data_encoding) if isinstance(v, unicode) else v)
                             for k, v in req.data.iteritems()])

        if referrer is None:
            referrer = self.get_referrer(self.url, url)
        if referrer:
            # Yes, it is a misspelling.
            req.headers.setdefault('Referer', referrer)

        return req

    def prepare_request(self, req):
        """
        Get a prepared request from a Request object.

        This method aims to be overloaded by children classes.
        """
        return self.session.prepare_request(req)

    REFRESH_RE = re.compile(r"^(?P<sleep>[\d\.]+)(; url=[\"']?(?P<url>.*?)[\"']?)?$", re.IGNORECASE)

    def handle_refresh(self, response):
        """
        Called by open, to handle Refresh HTTP header.

        It only redirect to the refresh URL if the sleep time is inferior to
        REFRESH_MAX.
        """
        if 'Refresh' not in response.headers:
            return response

        m = self.REFRESH_RE.match(response.headers['Refresh'])
        if m:
            # XXX perhaps we should not redirect if the refresh url is equal to the current url.
            url = m.groupdict().get('url', None) or response.request.url
            sleep = float(m.groupdict()['sleep'])

            if sleep <= self.REFRESH_MAX:
                self.logger.debug('Refresh to %s' % url)
                return self.open(url)
            else:
                self.logger.debug('Do not refresh to %s because %s > REFRESH_MAX(%s)' % (url, sleep, self.REFRESH_MAX))
                return response

        self.logger.warning('Unable to handle refresh "%s"' % response.headers['Refresh'])

        return response

    def get_referrer(self, oldurl, newurl):
        """
        Get the referrer to send when doing a request.
        If we should not send a referrer, it will return None.

        Reference: https://en.wikipedia.org/wiki/HTTP_referer

        :param oldurl: Current absolute URL
        :type oldurl: str or None

        :param newurl: Target absolute URL
        :type newurl: str

        :rtype: str or None
        """
        if oldurl is None:
            return None
        old = urlparse(oldurl)
        new = urlparse(newurl)
        # Do not leak secure URLs to insecure URLs
        if old.scheme == 'https' and new.scheme != 'https':
            return None
        # Reloading the page. Usually no referrer.
        if oldurl == newurl:
            return None
        # TODO maybe implement some *optional* privacy features:
        # * do not leak referrer to other domains (often breaks websites)
        # * send a fake referrer (root of the current domain)
        # * never send the referrer
        # Inspired by the RefControl Firefox addon.
        return oldurl


class UrlNotAllowed(Exception):
    """
    Raises by :class:`DomainBrowser` when `RESTRICT_URL` is set and trying to go
    on an url not matching `BASEURL`.
    """


class DomainBrowser(Browser):
    """
    A browser that handles relative URLs and can have a base URL (usually a domain).

    For instance self.location('/hello') will get http://weboob.org/hello
    if BASEURL is 'http://weboob.org/'.
    """

    BASEURL = None
    """
    Base URL, e.g. 'http://weboob.org/' or 'https://weboob.org/'
    See absurl().
    """

    RESTRICT_URL = False
    """
    URLs allowed to load.
    This can be used to force SSL (if the BASEURL is SSL) or any other leakage.
    Set to True to allow only URLs starting by the BASEURL.
    Set it to a list of allowed URLs if you have multiple allowed URLs.
    More complex behavior is possible by overloading url_allowed()
    """

    def __init__(self, baseurl=None, *args, **kwargs):
        super(DomainBrowser, self).__init__(*args, **kwargs)
        if baseurl is not None:
            self.BASEURL = baseurl

    def url_allowed(self, url):
        """
        Checks if we are allowed to visit an URL.
        See RESTRICT_URL.

        :param url: Absolute URL
        :type url: str
        :rtype: bool
        """
        if self.BASEURL is None or self.RESTRICT_URL is False:
            return True
        if self.RESTRICT_URL is True:
            return url.startswith(self.BASEURL)
        for restrict_url in self.RESTRICT_URL:
            if url.startswith(restrict_url):
                return True
        return False

    def absurl(self, uri, base=None):
        """
        Get the absolute URL, relative to the base URL.
        If BASEURL is None, it will try to use the current URL.
        If base is False, it will always try to use the current URL.

        :param uri: URI to make absolute. It can be already absolute.
        :type uri: str

        :param base: Base absolute URL.
        :type base: str or None or False

        :rtype: str
        """
        if not base:
            base = self.url
        if base is None or base is True:
            base = self.BASEURL
        return urljoin(base, uri)

    def open(self, req, *args, **kwargs):
        """
        Like :meth:`Browser.open` but hanldes urls without domains, using
        the :attr:`BASEURL` attribute.
        """
        uri = req.url if isinstance(req, requests.Request) else req

        url = self.absurl(uri)
        if not self.url_allowed(url):
            raise UrlNotAllowed(url)

        if isinstance(req, requests.Request):
            req.url = url
        else:
            req = url
        return super(DomainBrowser, self).open(req, *args, **kwargs)

    def go_home(self):
        """
        Go to the "home" page, usually the BASEURL.
        """
        return self.location(self.BASEURL or self.absurl('/'))


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
    one of URL objects, it returns a Page object. In case of location(), it
    stores it in self.page.

    Example:

    >>> from .pages import Page
    >>> class HomePage(Page):
    ...     pass
    ...
    >>> class ListPage(Page):
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

    def load_state(self, state):
        super(PagesBrowser, self).load_state(state)
        if 'url' in state:
            self.location(state['url'])

    def dump_state(self):
        state = super(PagesBrowser, self).dump_state()
        if self.page:
            state['url'] = self.page.url
        return state

    def open(self, *args, **kwargs):
        """
        Same method than
        :meth:`weboob.browser.browsers.DomainBrowser.open`, but the
        response contains an attribute `page` if the url matches any
        :class:`URL` object.
        """

        callback = kwargs.pop('callback', lambda response: response)

        # Have to define a callback to seamlessly process synchronous and
        # asynchronous requests, see :meth:`Browser.open` and its `async`
        # and `callback` params.
        def internal_callback(response):
            # Try to handle the response page with an URL instance.
            response.page = None
            for url in self._urls.itervalues():
                page = url.handle(response)
                if page is not None:
                    self.logger.debug('Handle %s with %s' % (response.url, page.__class__.__name__))
                    response.page = page
                    break

            if response.page is None:
                self.logger.debug('Unable to handle %s' % response.url)

            return callback(response)

        return super(PagesBrowser, self).open(callback=internal_callback, *args, **kwargs)

    def location(self, *args, **kwargs):
        """
        Same method than
        :meth:`weboob.browser.browsers.Browser.location`, but if the
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

        >>> from .pages import HTMLPage
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
        >>> b.list.go(pagenum=1) # doctest: +ELLIPSIS
        <weboob.browser.browsers.Page object at 0x...>
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

    def do_logout(self):
        self.session.cookies.clear()


class APIBrowser(DomainBrowser):
    def open(self, *args, **kwargs):
        if 'data' in kwargs:
            kwargs['data'] = json.dumps(kwargs['data'])
        if not 'headers' in kwargs:
            kwargs['headers'] = {}
        kwargs['headers']['Content-Type'] = 'application/json'

        return super(APIBrowser, self).open(*args, **kwargs)

    def request(self, *args, **kwargs):
        return self.open(*args, **kwargs).json()
