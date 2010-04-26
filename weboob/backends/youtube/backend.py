# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Christophe Benz, Romain Bignon

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

import re

from weboob.backend import BaseBackend
from weboob.capabilities.video import ICapVideoProvider

from .browser import YoutubeBrowser

class YoutubeBackend(BaseBackend, ICapVideoProvider):
    NAME = 'youtube'
    MAINTAINER = 'Christophe Benz'
    EMAIL = 'christophe.benz@gmail.com'
    VERSION = '0.1'
    DESCRIPTION = 'Youtube videos website'
    LICENSE = 'GPLv3'

    CONFIG = {}
    _browser = None

    def __getattr__(self, name):
        if name == 'browser':
            if not self._browser:
                self._browser = YoutubeBrowser()
            return self._browser
        raise AttributeError, name

    def need_url(func):
        def inner(self, *args, **kwargs):
            url = args[0]
            if (u'youtube.com' not in url) and not re.match('^[\w-]+$', url):
                return None
            return func(self, *args, **kwargs)
        return inner

    @need_url
    def get_video(self, _id):
        return self.browser.get_video(_id)

    SORTBY = ['', 'video_avg_rating', 'video_view_count', 'video_date_uploaded']
    def iter_search_results(self, pattern=None, sortby=ICapVideoProvider.SEARCH_RELEVANCE):
        return self.browser.iter_search_results(pattern, self.SORTBY[sortby])

    @need_url
    def iter_page_urls(self, mozaic_url):
        raise NotImplementedError()
