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

import logging
import re

from weboob.backend import BaseBackend
from weboob.capabilities.video import ICapVideoProvider, Video

from . import tools
from .browser import YoutubeBrowser


__all__ = ['YoutubeBackend']


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

    @classmethod
    def id2url(cls, _id):
        return _id if 'youtube.com' in _id else 'http://www.youtube.com/watch?v=%s' % _id

    def get_video(self, _id):
        return self.browser.get_video(_id)

    def iter_search_results(self, pattern=None, sortby=ICapVideoProvider.SEARCH_RELEVANCE, nsfw=False):
        try:
            import gdata.youtube.service
        except ImportError:
            logging.warning('Youtube backend search feature requires python-gdata package.')
            return
        yt_service = gdata.youtube.service.YouTubeService()
        query = gdata.youtube.service.YouTubeVideoQuery()
        query.orderby = ('relevance', 'rating', 'viewCount', 'published')[sortby]
        query.racy = 'include' if nsfw else 'exclude'
        if pattern:
            query.categories.extend('/%s' % search_term.lower().encode('utf-8') for search_term in pattern.split())
        feed = yt_service.YouTubeQuery(query)
        for entry in feed.entry:
            if entry.media.name:
                author = entry.media.name.text.decode('utf-8').strip()
            else:
                author = None
            yield Video(entry.id.text.split('/')[-1].decode('utf-8'),
                        title=entry.media.title.text.decode('utf-8').strip(),
                        author=author,
                        duration=int(entry.media.duration.seconds.decode('utf-8').strip()),
                        preview_url=entry.media.thumbnail[0].url.decode('utf-8').strip(),
                        id2url=tools.id2url)

    def iter_page_urls(self, mozaic_url):
        raise NotImplementedError()
