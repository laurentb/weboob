# -*- coding: utf-8 -*-

# Copyright(C) 2010  Christophe Benz, Romain Bignon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


import datetime
import logging

from weboob.core.backend import BaseBackend
from weboob.capabilities.video import ICapVideo

from .browser import YoutubeBrowser
from .video import YoutubeVideo


__all__ = ['YoutubeBackend']


class YoutubeBackend(BaseBackend, ICapVideo):
    NAME = 'youtube'
    MAINTAINER = 'Christophe Benz'
    EMAIL = 'christophe.benz@gmail.com'
    VERSION = '0.1'
    DESCRIPTION = 'Youtube videos website'
    LICENSE = 'GPLv3'

    CONFIG = {}
    BROWSER = YoutubeBrowser

    def get_video(self, _id):
        return self.browser.get_video(_id)

    def iter_search_results(self, pattern=None, sortby=ICapVideo.SEARCH_RELEVANCE, nsfw=False):
        import gdata.youtube.service
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
            yield YoutubeVideo(entry.id.text.split('/')[-1].decode('utf-8'),
                               title=entry.media.title.text.decode('utf-8').strip(),
                               author=author,
                               duration=datetime.timedelta(seconds=entry.media.duration.seconds.decode('utf-8').strip()),
                               thumbnail_url=entry.media.thumbnail[0].url.decode('utf-8').strip(),
                               )

    def iter_page_urls(self, mozaic_url):
        raise NotImplementedError()
