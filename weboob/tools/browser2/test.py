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

import requests
from nose.plugins.skip import SkipTest

from .browser import BaseBrowser, DomainBrowser, Weboob

from weboob.tools.json import json

# Those services can be run locally. More or less.
HTTPBIN = 'http://httpbin.org/'  # https://github.com/kennethreitz/httpbin
POSTBIN = 'http://www.postbin.org/'  # https://github.com/progrium/postbin
REQUESTBIN = 'http://requestb.in/'  # https://github.com/progrium/requestbin


def test_base():
    b = BaseBrowser()
    r = b.location(HTTPBIN + 'headers')
    assert isinstance(r.text, unicode)
    assert 'Firefox' in r.text
    assert 'python' not in r.text
    assert 'identity' not in r.text
    assert b.url == HTTPBIN + 'headers'

    r = b.location(HTTPBIN + 'gzip')
    assert 'Firefox' in r.text


def test_redirects():
    """
    Check redirects are followed
    """
    b = BaseBrowser()
    b.location(HTTPBIN + 'redirect/1')
    assert b.url == HTTPBIN + 'get'


def test_brokenpost():
    """
    Tests _fix_redirect()
    """
    try:
        b = BaseBrowser()
        # postbin is picky with empty posts. that's good!
        r = b.location(POSTBIN, {})
        # ensures empty data (but not None) does a POST
        assert r.request.method == 'POST'
        # ensure we were redirected after submitting a post
        assert len(r.url) >= len(POSTBIN)
        # send a POST with data
        b.location(r.url, {'hello': 'world'})
        r = b.location(r.url + '/feed')
        assert 'hello' in r.text
        assert 'world' in r.text
    except requests.HTTPError, e:
        if str(e).startswith('503 '):
            raise SkipTest('Quota exceeded')
        else:
            raise


def _getrqbin(b):
    """
    Get a RequestBin
    """
    # empty POST
    r = b.location(REQUESTBIN + 'api/v1/bins', '')
    name = json.loads(r.text)['name']
    assert name
    return name


def test_smartpost():
    """
    Checks we use POST or GET depending on the parameters
    """
    b = BaseBrowser()
    n = _getrqbin(b)

    r = b.location(REQUESTBIN + n)
    assert 'ok' in r.text
    r = b.location(REQUESTBIN + n + '?inspect')
    assert 'GET /%s' % n in r.text

    r = b.location(REQUESTBIN + n, {'hello': 'world'})
    assert 'ok' in r.text
    r = b.location(REQUESTBIN + n + '?inspect')
    assert 'POST /%s' % n in r.text
    assert 'hello' in r.text
    assert 'world' in r.text


def test_weboob():
    """
    Test the Weboob Profile
    """
    class BooBrowser(BaseBrowser):
        PROFILE = Weboob('0.0')

    b = BooBrowser()
    r = b.location(HTTPBIN + 'headers')
    assert 'weboob/0.0' in r.text
    assert 'identity' in r.text


def test_relative():
    """
    Check relative URL / domain handling
    """
    b = DomainBrowser()
    b.location(HTTPBIN)
    b.location('/ip')
    assert b.url == HTTPBIN + 'ip'

    assert b.absurl('/ip') == HTTPBIN + 'ip'
    b.location(REQUESTBIN)
    assert b.absurl('/ip') == REQUESTBIN + 'ip'
    b.BASEURL = HTTPBIN + 'aaaaaa'
    assert b.absurl('/ip') == HTTPBIN + 'ip'
    assert b.absurl('ip') == HTTPBIN + 'ip'
    assert b.absurl('/ip', False) == REQUESTBIN + 'ip'
    b.BASEURL = HTTPBIN + 'aaaaaa/'
    assert b.absurl('/') == HTTPBIN
    assert b.absurl('/bb') == HTTPBIN + 'bb'
    assert b.absurl('') == HTTPBIN + 'aaaaaa/'
    assert b.absurl('bb') == HTTPBIN + 'aaaaaa/bb'


def test_changereq():
    """
    Test overloading request defaults
    """
    b = BaseBrowser()
    r = b.location(HTTPBIN + 'headers', method='HEAD')
    assert r.text is None

    r = b.location(HTTPBIN + 'put', method='PUT', data={'hello': 'world'})
    assert 'hello' in r.text
    assert 'world' in r.text

    r = b.location(HTTPBIN + 'headers', headers={'User-Agent': 'Web Out of Browsers'})
    assert 'Web Out of Browsers' in r.text
    assert 'Firefox' not in r.text


def test_referrer():
    """
    Test automatic referrer setting
    """
    b = BaseBrowser()
    r = b.location(HTTPBIN + 'get')
    assert 'Referer' not in json.loads(r.text)['headers']
    r = b.location(HTTPBIN + 'headers')
    assert json.loads(r.text)['headers'].get('Referer') == HTTPBIN + 'get'
    r = b.location(HTTPBIN + 'headers')
    assert 'Referer' not in json.loads(r.text)['headers']

    assert b._get_referrer('https://example.com/', 'http://example.com/') is None
