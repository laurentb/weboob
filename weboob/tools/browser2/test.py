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

from datetime import datetime
from random import choice
import re
import string

from requests import HTTPError
from nose.plugins.skip import SkipTest
from nose.tools import assert_raises

from .browser import BaseBrowser, DomainBrowser, Weboob, UrlNotAllowed
from .cookiejar import CookieJar, CookiePolicy
from .cookies import Cookies

from weboob.tools.json import json

# Those services can be run locally. More or less.
HTTPBIN = 'http://httpbin.org/'  # https://github.com/kennethreitz/httpbin
POSTBIN = 'http://www.postbin.org/'  # https://github.com/progrium/postbin
REQUESTBIN = 'http://requestb.in/'  # https://github.com/progrium/requestbin

# if you change HTTPBIN, you should also change these URLs for some tests:
# redirect to http://httpbin.org/get
REDIRECTS1 = ('http://tinyurl.com/ouiboube-b2', 'http://bit.ly/st4Hcv')
# redirect to http://httpbin.org/cookies
REDIRECTS2 = ('http://tinyurl.com/7zp3jnr', 'http://bit.ly/HZCCX7')


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

    r = b.location(HTTPBIN + 'redirect/1')
    assert json.loads(r.text)['headers'].get('Referer') == HTTPBIN + 'redirect/1'
    assert r.url == HTTPBIN + 'get'

    # Normal redirect chain
    b.url = None
    r = b.location(HTTPBIN + 'redirect/4')
    assert json.loads(r.text)['headers'].get('Referer') == HTTPBIN + 'redirect/1'
    assert len(r.history) == 4
    assert r.history[3].request.url == HTTPBIN + 'redirect/1'
    assert r.history[3].request.headers.get('Referer') == HTTPBIN + 'redirect/2'
    assert r.history[2].request.url == HTTPBIN + 'redirect/2'
    assert r.history[2].request.headers.get('Referer') == HTTPBIN + 'redirect/3'
    assert r.history[1].request.url == HTTPBIN + 'redirect/3'
    assert r.history[1].request.headers.get('Referer') == HTTPBIN + 'redirect/4'
    assert r.history[0].request.url == HTTPBIN + 'redirect/4'
    assert r.history[0].request.headers.get('Referer') == None
    assert r.url == HTTPBIN + 'get'

    # Disable all referers
    r = b.location(HTTPBIN + 'redirect/2', referrer=False)
    assert json.loads(r.text)['headers'].get('Referer') == None
    assert len(r.history) == 2
    assert r.history[1].request.headers.get('Referer') == None
    assert r.history[0].request.headers.get('Referer') == None
    assert r.url == HTTPBIN + 'get'

    # Only overrides first referer
    r = b.location(HTTPBIN + 'redirect/2', referrer='http://example.com/')
    assert json.loads(r.text)['headers'].get('Referer') == HTTPBIN + 'redirect/1'
    assert len(r.history) == 2
    assert r.history[1].request.headers.get('Referer') == HTTPBIN + 'redirect/2'
    assert r.history[0].request.headers.get('Referer') == 'http://example.com/'
    assert r.url == HTTPBIN + 'get'

    # Don't follow
    r = b.location(HTTPBIN + 'redirect/2', allow_redirects=False)
    assert len(r.history) == 0
    assert r.url == HTTPBIN + 'redirect/2'
    assert r.status_code == 302


def test_redirect2():
    """
    More redirect tests
    """
    rurl = choice(REDIRECTS1)
    b = BaseBrowser()
    r = b.location(rurl)
    assert r.url == HTTPBIN + 'get'
    assert json.loads(r.text)['headers'].get('Referer') == rurl
    # TODO referrer privacy settings


def test_brokenpost():
    """
    Test empty POST and redirect after POST
    """
    raise SkipTest('PostBin is disabled')
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
    except HTTPError, e:
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

    # Give an absolute URL, should get it unaltered
    b.BASEURL = 'http://example.net/'
    assert b.absurl('http://example.com/aaa/bbb') == 'http://example.com/aaa/bbb'
    assert b.absurl('https://example.com/aaa/bbb') == 'https://example.com/aaa/bbb'

    # Schemeless absolute URL
    assert b.absurl('//example.com/aaa/bbb') == 'http://example.com/aaa/bbb'
    b.BASEURL = 'https://example.net/'
    assert b.absurl('//example.com/aaa/bbb') == 'https://example.com/aaa/bbb'


def test_allow_url():
    b = DomainBrowser()
    b.RESTRICT_URL = True
    assert b.url_allowed('http://example.com/')
    assert b.url_allowed('http://example.net/')

    b.BASEURL = 'http://example.com/'
    assert b.url_allowed('http://example.com/')
    assert b.url_allowed('http://example.com/aaa')
    assert not b.url_allowed('https://example.com/')
    assert not b.url_allowed('http://example.net/')
    assert not b.url_allowed('http://')

    b.BASEURL = 'https://example.com/'
    assert not b.url_allowed('http://example.com/')
    assert not b.url_allowed('http://example.com/aaa')
    assert b.url_allowed('https://example.com/')
    assert b.url_allowed('https://example.com/aaa/bbb')

    b.RESTRICT_URL = ['https://example.com/', 'http://example.com/']
    assert b.url_allowed('http://example.com/aaa/bbb')
    assert b.url_allowed('https://example.com/aaa/bbb')
    assert not b.url_allowed('http://example.net/aaa/bbb')
    assert not b.url_allowed('https://example.net/aaa/bbb')

    assert_raises(UrlNotAllowed, b.location, 'http://example.net/')
    assert_raises(UrlNotAllowed, b.open, 'http://example.net/')


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

    # Force another referrer
    r = b.location(HTTPBIN + 'get')
    r = b.location(HTTPBIN + 'headers', referrer='http://example.com/')
    assert json.loads(r.text)['headers'].get('Referer') == 'http://example.com/'

    # Force no referrer
    r = b.location(HTTPBIN + 'get')
    r = b.location(HTTPBIN + 'headers', referrer=False)
    assert 'Referer' not in json.loads(r.text)['headers']

    assert b.get_referrer('https://example.com/', 'http://example.com/') is None


def test_cookiepolicy():
    """
    Test cookie parsing and processing
    """
    policy = CookiePolicy()

    def bc(data):
        """
        build one cookie, and normalize it
        """
        cs = Cookies()
        cs.parse_response(data)
        for c in cs.itervalues():
            policy.normalize_cookie(c, 'http://example.com/')
            return c

    # parse max-age
    assert bc('__bwid=58244366; max-age=42; path=/').expires

    # security for received cookies
    assert policy.can_set(bc('k=v; domain=www.example.com'),
            'http://www.example.com/')
    assert policy.can_set(bc('k=v; domain=sub.example.com'),
            'http://www.example.com/')
    assert policy.can_set(bc('k=v; domain=sub.example.com'),
            'http://example.com/')
    assert policy.can_set(bc('k=v; domain=.example.com'),
            'http://example.com/')
    assert policy.can_set(bc('k=v; domain=www.example.com'),
            'http://example.com/')
    assert not policy.can_set(bc('k=v; domain=example.com'),
            'http://example.net/')
    assert not policy.can_set(bc('k=v; domain=.net'),
            'http://example.net/')
    assert not policy.can_set(bc('k=v; domain=www.example.net'),
            'http://www.example.com/')
    assert not policy.can_set(bc('k=v; domain=wwwexample.com'),
            'http://example.com/')
    assert not policy.can_set(bc('k=v; domain=.example.com'),
            'http://wwwexample.com/')

    # pattern matching domains
    assert not policy.domain_match('example.com', 's.example.com')
    assert policy.domain_match('.example.com', 's.example.com')
    assert not policy.domain_match('.example.com', 'example.com')  # yep.
    assert policy.domain_match('s.example.com', 's.example.com')
    assert not policy.domain_match('s.example.com', 's2.example.com')
    assert policy.domain_match_list(True, 'example.com')
    assert not policy.domain_match_list([], 'example.com')
    assert policy.domain_match_list(['example.net', 'example.com'], 'example.com')
    assert not policy.domain_match_list(['example.net', 'example.org'], 'example.com')


def test_cookiejar():
    """
    Test adding, removing, finding cookies to and from the jar
    """
    def bc(data):
        """
        build one cookie
        """
        cs = Cookies()
        cs.parse_response(data)
        for c in cs.itervalues():
            return c

    # filtering cookies
    cookie0 = bc('j=v; domain=www.example.com; path=/')
    cookie1 = bc('k=v1; domain=www.example.com; path=/; secure')
    cookie2 = bc('k=v2; domain=.example.com; path=/')
    cookie3 = bc('k=v3; domain=www.example.com; path=/lol/cat/')
    cookie4 = bc('k=v4; domain=www.example.com; path=/lol/')

    cj = CookieJar(CookiePolicy())
    cj.set(cookie0)
    cj.set(cookie1)
    cj.set(cookie2)
    cj.set(cookie3)
    cj.set(cookie4)

    assert len(cj.all()) == 5  # all cookies
    assert len(cj.all(path='/')) == 3  # all cookies except the ones with deep paths
    assert len(cj.all(name='k')) == 4  # this excludes cookie0
    assert len(cj.all(domain='example.com')) == 0  # yep
    assert len(cj.all(domain='s.example.com')) == 1  # cookie2
    assert len(cj.all(domain='.example.com')) == 1  # cookie2 (exact match)
    assert len(cj.all(domain='www.example.com')) == 5  # all cookies
    assert len(cj.all(domain='www.example.com', path="/lol/")) == 4  # all + cookie4
    assert len(cj.all(domain='www.example.com', path="/lol/cat")) == 4  # all + cookie4
    assert len(cj.all(domain='www.example.com', path="/lol/cat/")) == 5  # all + cookie4 + cookie3
    assert len(cj.all(secure=True)) == 1  # cookie1
    assert len(cj.all(secure=False)) == 4  # all except cookie1

    assert cj.get(domain='www.example.com', path="/lol/") is cookie4
    assert cj.get(domain='www.example.com', path="/lol/cat/") is cookie3
    assert cj.get(domain='www.example.com', path="/") is cookie1
    assert cj.get(name='j', domain='www.example.com', path="/") is cookie0
    assert cj.get(name='k', domain='www.example.com', path="/") is cookie1
    assert cj.get(name='k', domain='s.example.com', path="/") is cookie2
    assert cj.get(name='k', domain='www.example.com', path="/aaa") is cookie1
    assert cj.get(domain='www.example.com', path='/') is cookie1
    assert cj.get(domain='www.example.com', path='/', secure=False) is cookie0
    assert cj.get(domain='www.example.com', path='/', secure=True) is cookie1

    # this is just not API choice, but how browsers act
    assert cj.for_request('http://www.example.com/') == {'k': 'v2', 'j': 'v'}
    assert cj.for_request('https://www.example.com/') == {'k': 'v1', 'j': 'v'}
    assert cj.for_request('http://www.example.com/lol/') == {'k': 'v4', 'j': 'v'}
    assert cj.for_request('http://s.example.com/lol/') == {'k': 'v2'}
    assert cj.for_request('http://example.com/lol/') == {}

    # remove/add/replace
    assert cj.remove(cookie1) is True
    assert cj.get(secure=True) is None
    cj.set(cookie1)
    assert cj.get(secure=True) is cookie1
    cookie5 = bc('k=w; domain=www.example.com; path=/; secure')
    cj.set(cookie5)
    assert cj.get(secure=True) is cookie5
    assert len(cj.all(secure=True)) == 1
    # not the same cookie, but the same identifiers
    assert cj.remove(cookie1) is True

    cj.clear()
    cookie6 = bc('e1=1; domain=www.example.com; path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;')
    cookie7 = bc('e2=1; domain=www.example.com; path=/; Expires=Thu, 01 Jan 2010 00:00:01 GMT;')
    now = datetime(2000, 01, 01)
    cj.set(cookie0)
    cj.set(cookie6)
    cj.set(cookie7)

    assert cj.for_request('http://www.example.com/', now) == {'e2': '1', 'j': 'v'}
    assert cj.for_request('http://www.example.com/', datetime(2020, 01, 01)) == {'j': 'v'}

    assert len(cj.all()) == 3
    cj.flush(now)
    assert len(cj.all()) == 2
    assert cj.remove(cookie6) is False  # already removed
    cj.flush(now, session=True)
    assert len(cj.all()) == 1


def test_buildcookie():
    """
    Test easy cookie building
    """
    cj = CookieJar(CookiePolicy())
    c = cj.build('kk', 'vv', 'http://example.com/')
    assert c.domain == 'example.com'
    assert not c.secure
    assert c.path == '/'

    c = cj.build('kk', 'vv', 'http://example.com/', path='/plop/', wildcard=True)
    assert c.domain == '.example.com'

    assert c.path == '/plop/'
    c = cj.build('kk', 'vv', 'http://example.com/plop/')
    assert c.path == '/plop/'
    c = cj.build('kk', 'vv', 'http://example.com/plop/plap')
    assert c.path == '/plop/'
    c = cj.build('kk', 'vv', 'http://example.com/plop/?http://example.net/plip/')
    assert c.path == '/plop/'
    assert c.domain == 'example.com'
    c = cj.build('kk', 'vv', 'http://example.com/plop/plap', path='/')
    assert c.path == '/'

    c = cj.build('kk', 'vv', 'https://example.com/')
    assert c.domain == 'example.com'
    assert c.secure

    # check the cookie works
    c.name = 'k'
    c.value = 'v'
    cj.set(c)
    assert cj.for_request('https://example.com/') == {'k': 'v'}
    assert cj.for_request('http://example.com/') == {}


def test_cookienav():
    """
    Test browsing while getting new cookies
    """
    b = BaseBrowser()
    r = b.location(HTTPBIN + 'cookies')
    assert len(json.loads(r.text)['cookies']) == 0

    r = b.location(HTTPBIN + 'cookies/set/hello/world')
    assert len(json.loads(r.text)['cookies']) == 1
    assert json.loads(r.text)['cookies']['hello'] == 'world'
    r = b.location(HTTPBIN + 'cookies/set/hello2/world2')
    assert len(json.loads(r.text)['cookies']) == 2
    assert json.loads(r.text)['cookies']['hello2'] == 'world2'

    r = b.location(REQUESTBIN)
    assert 'session' in r.cookies  # requestbin should give this by default
    assert 'hello' not in r.cookies  # we didn't send the wrong cookie
    # return to httpbin, check we didn't give the wrong cookie
    r = b.location(HTTPBIN + 'cookies')
    assert 'session' not in json.loads(r.text)['cookies']

    # override cookies temporarily
    r = b.location(HTTPBIN + 'cookies', cookies={'bla': 'bli'})
    assert len(json.loads(r.text)['cookies']) == 1
    assert json.loads(r.text)['cookies']['bla'] == 'bli'
    # reload, the "fake" cookie should not be there
    r = b.location(HTTPBIN + 'cookies')
    assert len(json.loads(r.text)['cookies']) == 2
    assert 'bla' not in json.loads(r.text)['cookies']


def test_cookieredirect():
    """
    Test cookie redirection security
    """
    rurl = choice(REDIRECTS2)

    b = BaseBrowser()
    r = b.location(HTTPBIN + 'cookies')
    assert len(json.loads(r.text)['cookies']) == 0

    # add a cookie to the redirection service domain (not the target!)
    cookie = b.cookies.build('k', 'v1', rurl)
    b.cookies.set(cookie)
    r = b.location(rurl)
    assert r.url == HTTPBIN + 'cookies'
    # the cookie was not forwarded; it's for another domain
    # this is important for security reasons,
    # and because python-requests tries to do it by default!
    assert len(json.loads(r.text)['cookies']) == 0

    # add a cookie for the target
    cookie = b.cookies.build('k', 'v2', HTTPBIN)
    b.cookies.set(cookie)
    r = b.location(rurl)
    assert r.url == HTTPBIN + 'cookies'
    assert len(json.loads(r.text)['cookies']) == 1
    assert json.loads(r.text)['cookies']['k'] == 'v2'

    # check all cookies sent in the request chain
    assert r.cookies == {'k': 'v2'}
    assert r.history[0].cookies['k'] == 'v1'  # some services add other cookies


def test_cookie_srv1():
    """
    Test cookie in real conditions (service 1)
    """
    class TestBrowser(DomainBrowser):
        BASEURL = 'http://www.mria-arim.ca/'

    b = TestBrowser()
    b.location('testCookies.asp')
    # TODO this is also a good place to test form parsing/submission
    b.location('testCookies.asp', {'makeMe': 'Create Cookie'})
    r = b.location('testCookies.asp', {'testMe': 'Test Browser'})
    assert 'Your Browser accepts cookies' in r.text


def test_cookie_srv2():
    """
    Test cookie in real conditions (service 2)
    """
    def randtext():
        return ''.join(choice(string.digits + string.letters) for _ in xrange(32))

    class TestBrowser(DomainBrowser):
        BASEURL = 'http://www.html-kit.com/tools/cookietester/'

        def cookienum(self):
            return int(re.search('Number of cookies received: (\d+)',
                    self.response.text).groups()[0])

        def mypost(self, **data):
            return self.location('', data)

    b = TestBrowser()
    b.home()
    assert b.cookienum() == 0

    r1 = randtext()
    r1v = randtext()

    # TODO this is also a good place to test form parsing/submission
    # get a new cookie
    r = b.mypost(cn=r1, cv=r1v)
    assert b.cookienum() == 1
    assert r1 in r.text
    assert r1v in r.text

    # cookie deletion
    r = b.mypost(cr=r1)
    assert b.cookienum() == 0
    assert r1 not in r.text
    assert r1v not in r.text

    # om nom nom
    b.mypost(cn=randtext(), cv=randtext())
    b.mypost(cn=randtext(), cv=randtext())
    b.mypost(cn=randtext(), cv=randtext())
    b.mypost(cn=randtext(), cv=randtext())
    assert b.cookienum() == 4
