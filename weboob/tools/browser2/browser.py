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
from copy import deepcopy

import requests

from .cookiejar import CookieJar, CookiePolicy


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
        session.config['base_headers']['User-Agent'] = 'weboob/%s' % self.version


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
        session.config['base_headers'] = {'Accept-Language': 'en-us,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:10.0.3) Gecko/20100101 Firefox/10.0.3',
            'DNT': '1'}
        # It also has "Connection: Keep-Alive", that should only be added this way:
        session.config['keep_alive'] = True


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
        session.config['base_headers'].update({'Accept': '*/*',
            'User-Agent': 'Wget/%s' % self.version})
        session.config['keep_alive'] = True


class BaseBrowser(object):
    """
    Simple browser class.
    Act like a browser, and don't try to do too much.
    """

    PROFILE = Firefox()
    TIMEOUT = 10.0
    COOKIE_POLICY = CookiePolicy()

    def __init__(self):
        self._setup_session(self.PROFILE)
        self._setup_cookies(self.COOKIE_POLICY)
        self.url = None
        self.response = None

    def _setup_cookies(self, policy):
        """
        Create and configure a cookie jar.

        Overload this method to set custom options, or even change the class.
        """
        self.cookies = CookieJar(policy)

    def _setup_session(self, profile):
        """
        Set up a python-requests session for our usage.
        """
        session = requests.Session()

        if self.TIMEOUT:
            session.timeout = self.TIMEOUT
        # Raise exceptions on HTTP errors
        session.config['safe_mode'] = False
        session.config['danger_mode'] = True
        # TODO max_retries?
        # TODO connect config['verbose'] to our logger

        profile.setup_session(session)

        self.session = session

    def follow_redirects(self, response, orig_args=None):
        """
        Follow redirects *properly*.
        * Mimic what browsers do on 302
        * Handle cookies securely

        This method is called by open() or location() unless allow_redirects is False.

        Returns a new Response object with the history of previous
        responses in it.

        :type response: :class:`requests.Response`
        :type orig_args: dict
        :rtype: :class:`requests.Response`
        """
        # The response chain. We start with the one we got.
        responses = [response]
        request = response.request

        # Default method for redirects
        orig_args = orig_args or {}
        orig_args.setdefault('method', request.method)
        orig_args.setdefault('data', request.data)
        # If we have the original arguments, take them, and fix them
        orig_args.pop('url', None)
        orig_referrer = orig_args.pop('referrer', None)
        # Avoid infinite loops
        orig_args['allow_redirects'] = False

        # TL;DR: Web browsers and web developers suck.
        #
        # Most browsers do not follow the RFC for HTTP 302
        # but python-requests does.
        # And web developers assume we don't follow it either:
        # https://en.wikipedia.org/wiki/Post/Redirect/Get
        #
        # Later python-request versions do it that way, but to stay
        # compatible with older versions, we use this.
        while request.allow_redirects is False \
        and response.status_code in requests.models.REDIRECT_STATI \
        and 'location' in response.headers:
            ## This is from requests.models._build_response
            response.content  # Consume socket so it can be released

            if len(responses) > response.config.get('max_redirects'):
                raise requests.exceptions.TooManyRedirects()

            # Release the connection back into the pool.
            response.raw.release_conn()
            ## End of code from requests.models._build_response

            # http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.3.4
            if response.status_code == requests.codes.see_other:
                orig_args['method'] = 'GET'
                orig_args['data'] = None
                orig_args['files'] = None

            if not request.config.get('strict_mode'):
                # Do the same as Google Chrome.
                # http://git.chromium.org/gitweb/?p=chromium/src/net.git;a=blob;f=url_request/url_request.cc;h=8597917f0cbf49c84b3bdae3a7bebacbc264f1e0;hb=HEAD#l673
                if (response.status_code == 303 and request.method != 'HEAD') \
                or (response.status_code in (requests.codes.moved, requests.codes.found) and request.method == 'POST'):
                    # Once we use GET, all next requests will use GET.
                    orig_args['method'] = 'GET'
                    orig_args['data'] = None
                    orig_args['files'] = None

            ## This is from requests.models._build_response
            url = response.headers['location']

            # Handle redirection without scheme (see: RFC 1808 Section 4)
            if url.startswith('//'):
                parsed_rurl = urlparse(response.url)
                url = '%s:%s' % (parsed_rurl.scheme, url)

            # Facilitate non-RFC2616-compliant 'location' headers
            # (e.g. '/path/to/resource' instead of 'http://domain.tld/path/to/resource')
            if not urlparse(url).netloc:
                url = urljoin(response.url,
                                # Compliant with RFC3986, we percent
                                # encode the url.
                                requests.utils.requote_uri(url))

            ## End of code from requests.models._build_response

            if orig_referrer is False:
                # Referer disabled in original request, disable in next
                referrer = orig_referrer
            else:
                # Guess from last response
                referrer = self.get_referrer(response.url, url)

            call_args = deepcopy(orig_args)
            response = self.open(url, referrer=referrer, **call_args)
            responses.append(response)

        # get the final response
        response = responses.pop()
        # _build_response does this
        response.history = responses
        request.response = response

        return response

    def location(self, url, data=None,
            allow_redirects=True, referrer=None,
            **kwargs):
        """
        Like open() but also changes the current URL and response.
        This is the most common method to request web pages.

        Other than that, has the exact same behavior of open().
        """
        response = self.open(url, data, allow_redirects, referrer, **kwargs)
        self.response = response
        self.url = self.response.url
        return response

    def open(self, url, data=None,
            allow_redirects=True, referrer=None,
            **kwargs):
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
        kwargs = deepcopy(kwargs)
        orig_args = deepcopy(kwargs)
        orig_args['referrer'] = referrer

        # guess method
        method = kwargs.pop('method', None)
        if method is None:
            if data is None:
                method = 'GET'
            else:
                method = 'POST'
        kwargs['data'] = data

        # python-requests or urllib3 does not handle
        # empty POST requests properly, so some websites refuse it.
        if data is not None and len(data) == 0:
            kwargs.setdefault('headers', {}).setdefault('Content-Length', '0')

        # Use our own redirection handling
        # python-requests's one sucks too much to be allowed.
        kwargs.setdefault('config', {}).setdefault('strict_mode', False)
        kwargs['allow_redirects'] = False

        if referrer is None:
            referrer = self.get_referrer(self.url, url)
        if referrer:
            # Yes, it is a misspelling.
            kwargs.setdefault('headers', {}).setdefault('Referer', referrer)

        cookies = kwargs.pop('cookies', None)
        # get the relevant cookies for the URL
        # from the jar (unless they are overriden)
        if cookies is None:
            cookies = self.cookies.for_request(url)
        kwargs['cookies'] = cookies
        # erase all cookies, python-requests does not handle them securely
        # and tries to merge them with provided cookies!
        self.session.cookies.clear()

        # call python-requests
        response = self.session.request(method, url, **kwargs)

        # read cookies
        self.cookies.from_response(response)

        if allow_redirects:
            response = self.follow_redirects(response, orig_args)

        # erase all cookies again
        # to prevent leakage when using session.request() directly
        self.session.cookies.clear()

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
        if base is None:
            base = self.BASEURL
        if base is None or base is False:
            base = self.url
        return urljoin(base, uri)

    def open(self, uri, *args, **kwargs):
        return super(DomainBrowser, self).open(self.absurl(uri), *args, **kwargs)

    def home(self):
        """
        Go to the "home" page, usually the BASEURL.
        """
        return self.location(self.BASEURL or self.absurl('/'))
