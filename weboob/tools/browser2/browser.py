# -*- coding: utf-8 -*-

# Copyright(C) 2012 Laurent Bachelier
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

from urlparse import urlparse, urljoin

try:
    import requests
except ImportError:
    raise ImportError('Please install python-requests >= 2.0')


from weboob.tools.log import getLogger


# TODO define __all__


class Profile(object):
    """
    A profile represents the way Browser should act.
    Usually it is to mimic a real browser.
    """

    def setup_session(self, session):
        """
        Change default headers, set up hooks, etc.

        Warning: Do not enable lzma, bzip or bzip2, sdch encodings
        as python-requests does not support it yet.
        In doubt, do not change the default Accept-Encoding header
        of python-requests.
        """
        raise NotImplementedError()


class Weboob(Profile):
    """
    It's us!
    Recommended for Weboob-friendly websites only.
    """

    def __init__(self, version):
        self.version = version

    def setup_session(self, session):
        session.headers['User-Agent'] = 'weboob/%s' % self.version


class Firefox(Profile):
    """
    Try to mimic a specific version of Firefox.
    Ideally, it should follow the current ESR Firefox:
    https://www.mozilla.org/en-US/firefox/organizations/all.html
    Do not change the Firefox version without changing the Gecko one!
    """

    def setup_session(self, session):
        """
        Set up headers for a standard Firefox request
        (except for DNT which isn't on by default but is a good idea).

        The goal is to be unidentifiable.
        """
        # Replace all base requests headers
        # https://developer.mozilla.org/en/Gecko_user_agent_string_reference
        # https://bugzilla.mozilla.org/show_bug.cgi?id=572650
        session.headers = {
            'Accept-Language': 'en-us,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:10.0.3) Gecko/20100101 Firefox/10.0.3',
            'DNT': '1'}
        # It also has "Connection: Keep-Alive", that should only be added this way:
        #session.config['keep_alive'] = True


class Wget(Profile):
    """
    Common alternative user agent.
    Some websites will give you a version with less JavaScript.
    Some others could ban you (after all, wget is not a real browser).
    """
    def __init__(self, version='1.11.4'):
        self.version = version

    def setup_session(self, session):
        # Don't remove base headers, if websites want to block fake browsers,
        # they will probably block any wget user agent anyway.
        session.headers.update({
            'Accept': '*/*',
            'User-Agent': 'Wget/%s' % self.version})
        #session.config['keep_alive'] = True


class BaseBrowser(object):
    """
    Simple browser class.
    Act like a browser, and don't try to do too much.
    """

    PROFILE = Firefox()
    TIMEOUT = 10.0

    def __init__(self, logger=None):
        self.logger = getLogger('browser', logger)
        self._setup_session(self.PROFILE)
        self.url = None
        self.response = None

    def _setup_session(self, profile):
        """
        Set up a python-requests session for our usage.
        """
        session = requests.Session()

        if self.TIMEOUT:
            session.timeout = self.TIMEOUT
        # Raise exceptions on HTTP errors
        #session.config['safe_mode'] = False
        #session.config['danger_mode'] = True
        ## weboob only can provide proxy and auth options
        #session.config['trust_env'] = False
        # TODO max_retries?
        # TODO connect config['verbose'] to our logger

        profile.setup_session(session)

        self.session = session

    def location(self, url, **kwargs):
        """
        Like open() but also changes the current URL and response.
        This is the most common method to request web pages.

        Other than that, has the exact same behavior of open().
        """
        response = self.open(url, **kwargs)
        self.response = response
        self.url = self.response.url
        return response

    def open(self, url, referrer=None, **kwargs):
        """
        Make an HTTP request like a browser does:
         * follow redirects (unless disabled)
         * handle cookies
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

        :param url: URL
        :type url: str

        :param data: POST data
        :type url: str or dict or None

        :param referrer: Force referrer. False to disable sending it, None for guessing
        :type referrer: str or False or None

        :rtype: :class:`requests.Response`
        """
        if isinstance(url, requests.Request):
            req = url
            url = req.url
        else:
            req = requests.Request(url=url, **kwargs)

        # guess method
        if req.method is None:
            if req.data is None:
                req.method = 'POST'
            else:
                req.method = 'GET'

        # Python httplib does not handle
        # empty POST requests properly, so some websites refuse it.
        # https://github.com/kennethreitz/requests/issues/223
        # http://bugs.python.org/issue14721
        if req.data is not None and len(req.data) == 0:
            req.headers.setdefault('Content-Length', '0')

        if referrer is None:
            referrer = self.get_referrer(self.url, url)
        if referrer:
            # Yes, it is a misspelling.
            req.headers.setdefault('Referer', referrer)

        preq = self.session.prepare_request(req)

        # call python-requests
        response = self.session.send(preq)

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
    pass


class DomainBrowser(BaseBrowser):
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

    """
    URLs allowed to load.
    This can be used to force SSL (if the BASEURL is SSL) or any other leakage.
    Set to True to allow only URLs starting by the BASEURL.
    Set it to a list of allowed URLs if you have multiple allowed URLs.
    More complex behavior is possible by overloading url_allowed()
    """
    RESTRICT_URL = False

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
        uri = req.url if isinstance(req, requests.Request) else req

        url = self.absurl(uri)
        if not self.url_allowed(url):
            raise UrlNotAllowed(url)

        if isinstance(req, requests.Request):
            req.url = url
        else:
            req = url
        return super(DomainBrowser, self).open(req, *args, **kwargs)

    def home(self):
        """
        Go to the "home" page, usually the BASEURL.
        """
        return self.location(self.BASEURL or self.absurl('/'))
