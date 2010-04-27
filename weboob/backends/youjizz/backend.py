# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Roger Philibert

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

from weboob.backend import BaseBackend
from weboob.capabilities.video import ICapVideoProvider

from .browser import YoujizzBrowser


__all__ = ['YoujizzBackend']


class YoujizzBackend(BaseBackend, ICapVideoProvider):
    NAME = 'youjizz'
    MAINTAINER = 'Roger Philibert'
    EMAIL = 'roger.philibert@gmail.com'
    VERSION = '0.1'
    DESCRIPTION = 'Youjizz videos website'
    LICENSE = 'GPLv3'

    CONFIG = {}
    _browser = None

    def __getattr__(self, name):
        if name == 'browser':
            if not self._browser:
                self._browser = YoujizzBrowser()
            return self._browser
        raise AttributeError, name

    @classmethod
    def id2url(cls, _id):
        return 'http://www.youjizz.com/videos/%s.html' % _id

    def check_url(func):
        def inner(self, *args, **kwargs):
            url = args[0]
            if isinstance(url, (str,unicode)) and not url.isdigit() and u'youjizz.com' not in url:
                return None
            return func(self, *args, **kwargs)
        return inner

    @check_url
    def get_video(self, _id):
        return self.browser.get_video(_id)

    @check_url
    def iter_page_urls(self, mozaic_url):
        return self.browser.iter_page_urls(mozaic_url)

    def iter_search_results(self, pattern=None, sortby=ICapVideoProvider.SEARCH_RELEVANCE, nsfw=False):
        if not nsfw:
            return iter(set())
        return self.browser.iter_search_results(pattern)
