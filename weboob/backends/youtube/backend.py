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

from weboob.capabilities.video import ICapVideo
from weboob.tools.backend import BaseBackend
from weboob.tools.misc import iter_fields

from .browser import YoutubeBrowser
from .pages import ForbiddenVideo
from .video import YoutubeVideo


__all__ = ['YoutubeBackend']


class YoutubeBackend(BaseBackend, ICapVideo):
    NAME = 'youtube'
    MAINTAINER = 'Christophe Benz'
    EMAIL = 'christophe.benz@gmail.com'
    VERSION = '0.1'
    DESCRIPTION = 'Youtube videos website'
    LICENSE = 'GPLv3'

    BROWSER = YoutubeBrowser

    def get_video(self, _id, video=None):
        try:
            browser_video = self.browser.get_video(_id)
        except ForbiddenVideo:
            if video is None:
                return None
            else:
                raise
        if video is None:
            return browser_video
        else:
            for k, v in iter_fields(browser_video):
                if v and getattr(video, k) != v:
                    setattr(video, k, v)
            return video

    def iter_search_results(self, pattern=None, sortby=ICapVideo.SEARCH_RELEVANCE, nsfw=False, required_fields=None):
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
            video = YoutubeVideo(entry.id.text.split('/')[-1].decode('utf-8'),
                                 title=entry.media.title.text.decode('utf-8').strip(),
                                 author=author,
                                 duration=datetime.timedelta(seconds=int(entry.media.duration.seconds.decode('utf-8').strip())),
                                 thumbnail_url=entry.media.thumbnail[0].url.decode('utf-8').strip(),
                                 )
            if required_fields is not None:
                missing_required_fields = set(required_fields) - set(k for k, v in iter_fields(video) if v)
                if missing_required_fields:
                    logging.debug(u'Completing missing required fields: %s' % missing_required_fields)
                    try:
                        self.get_video(video.id, video=video)
                    except ForbiddenVideo, e:
                        logging.debug(e)
                        continue
                    else:
                        missing_required_fields = set(required_fields) - set(k for k, v in iter_fields(video) if v)
                        if missing_required_fields:
                            raise Exception(u'Could not load all required fields. Missing: %s' % missing_required_fields)
            yield video

    def iter_page_urls(self, mozaic_url):
        raise NotImplementedError()
