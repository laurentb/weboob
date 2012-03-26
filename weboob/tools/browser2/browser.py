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

import requests
from requests.status_codes import codes


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


class Browser(object):
    PROFILE = Firefox()
    TIMEOUT = 10.0

    def __init__(self):
        profile = self.PROFILE
        self._setup_session(profile)
        self.url = None
        self.response = None

    def _setup_session(self, profile):
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

        Most browsers do not follow the RFC for HTTP 301 and 302
        but python-requests does.
        And web developers assume we don't follow it either.
        https://en.wikipedia.org/wiki/Post/Redirect/Get

        Gets a Response, and returns a new Response.
        Used as a 'response' hook for python-requests.

        This is a hack, it would be better as an option in python-requests.
        """
        request = response.request
        # If the request wasn't redirected, and is a redirection,
        # and we allowed it to be fixed,
        # restart the request building, but with a changed action.
        if request.allow_redirects is False \
        and request.response.status_code in (codes.moved, codes.found) \
        and request.config.get('fix-redirect'):
            # force the next request to be GET
            real_method = request.method
            request.method = 'GET'
            real_data = request.data
            request.data = None

            # build the response again
            request.allow_redirects = True
            request._build_response(response.raw)

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
        Makes a GET request, or a POST if data is provided.

        Call this if you do not want to "visit" the URL (for instance, you
        are downloading a file).
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


def test_base():
    b = Browser()
    r = b.location('http://httpbin.org/headers')
    assert isinstance(r.text, unicode)
    assert 'Firefox' in r.text
    assert 'python' not in r.text
    assert 'identity' not in r.text
    assert b.url == 'http://httpbin.org/headers'


def test_redirects():
    b = Browser()
    b.location('http://httpbin.org/redirect/1')
    assert b.url == 'http://httpbin.org/get'


def test_brokenpost():
    """
    Tests _fix_redirect()
    """
    b = Browser()
    # postbin is picky with empty posts. that's good!
    r = b.location('http://www.postbin.org/', {})
    # ensures empty data (but not None) does a POST
    assert r.request.method == 'POST'
    # ensure we were redirected after submitting a post
    assert len(r.url) >= len('http://www.postbin.org/')
    # send a POST with data
    b.location(r.url, {'hello': 'world'})
    r = b.location(r.url + '/feed')
    assert 'hello' in r.text
    assert 'world' in r.text


def test_weboob():
    class BooBrowser(Browser):
        PROFILE = Weboob('0.0')

    b = BooBrowser()
    r = b.location('http://httpbin.org/headers')
    assert 'weboob/0.0' in r.text
    assert 'identity' in r.text
