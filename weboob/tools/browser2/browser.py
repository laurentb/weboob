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

import urlparse

import requests
from requests.status_codes import codes


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

    def __init__(self):
        profile = self.PROFILE
        self._setup_session(profile)
        self.url = None
        self.response = None

    def _setup_session(self, profile):
        """
        Set up a python-requests session for our usage.
        """
        session = requests.Session()

        # Raise exceptions on HTTP errors
        session.config['safe_mode'] = False
        session.config['danger_mode'] = True
        # TODO max_retries?
        # TODO connect config['verbose'] to our logger

        # TODO find a way to have multiple session hooks
        # lists don't work in this context
        session.hooks['response'] = self._fix_redirect

        profile.setup_session(session)

        self.session = session

    def _fix_redirect(self, response):
        """
        TL;DR: Web browsers and web developers suck.

        Most browsers do not follow the RFC for HTTP 302
        but python-requests does.
        And web developers assume we don't follow it either:
        https://en.wikipedia.org/wiki/Post/Redirect/Get

        Gets a Response, and returns a new Response.
        Used as a 'response' hook for python-requests.

        This is a hack, it would be better as an option in python-requests.

        What we do is run again the response building, but this time with allow_redirects,
        and with a fake method and data if we have a HTTP 302.
        """
        request = response.request
        # If the request wasn't redirected, and is a redirection,
        # and we allowed it to be fixed,
        # restart the request building, but with a changed action.
        if request.allow_redirects is False \
        and request.response.status_code in requests.models.REDIRECT_STATI \
        and request.config.get('fix-redirect'):
            if request.response.status_code is codes.found:
                # force the next request to be GET
                real_method = request.method
                request.method = 'GET'
                real_data = request.data
                request.data = None

            # build the response again
            request.allow_redirects = True
            request._build_response(response.raw)

            if request.response.status_code is codes.found:
                # restore info
                request.method = real_method
                request.data = real_data

            return request.response

    def location(self, url, data=None, fix_redirect=True, **kwargs):
        """
        Like open() but also changes the current URL and response.
        This is the most common method to request web pages.
        """
        response = self.open(url, data, fix_redirect, **kwargs)
        self.response = response
        self.url = self.response.url
        return response

    def open(self, url, data=None, fix_redirect=True, **kwargs):
        """
        Wrapper around request().
        Makes a GET request, or a POST if data is not None.
        An empty data *will* make a post.

        Call this if you do not want to "visit" the URL (for instance, you
        are downloading a file).

        :param url: URL
        :type url: str

        :rtype: :class:`requests.Response`
        """
        method = kwargs.pop('method', None)
        if method is None:
            if data is None:
                method = 'GET'
            else:
                method = 'POST'
        kwargs['data'] = data
        if fix_redirect:
            kwargs.setdefault('config', {}).setdefault('fix-redirect', True)
        response = self.request(method, url, **kwargs)
        return response

    def request(self, *args, **kwargs):
        """
        Creates a Request object and calls it.
        Takes the sames arguments as request.request()
        Returns a Response object.

        Most of the time, you should use location() or open().
        """
        # python-requests or urllib3 does not handle
        # empty POST requests properly, so some websites refuse it.
        data = kwargs.get('data')
        if data is not None and len(data) == 0:
            kwargs.setdefault('headers', {}).setdefault('Content-Length', '0')
        kwargs.setdefault('timeout', self.TIMEOUT)
        return self.session.request(*args, **kwargs)


class DomainBrowser(BaseBrowser):
    """
    A browser that handles relative URLs.

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
        return urlparse.urljoin(base, uri)

    def open(self, uri, *args, **kwargs):
        return BaseBrowser.open(self, self.absurl(uri), *args, **kwargs)

    def home(self):
        return self.location('/')
