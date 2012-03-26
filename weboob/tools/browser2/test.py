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

from .browser import Browser, Weboob

import requests

from nose.plugins.skip import SkipTest


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
    try:
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
    except requests.HTTPError, e:
        if str(e).startswith('503 '):
            raise SkipTest('Quota exceeded')
        else:
            raise


def test_weboob():
    class BooBrowser(Browser):
        PROFILE = Weboob('0.0')

    b = BooBrowser()
    r = b.location('http://httpbin.org/headers')
    assert 'weboob/0.0' in r.text
    assert 'identity' in r.text
