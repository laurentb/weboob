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


from __future__ import with_statement

import datetime

from weboob.capabilities.video import ICapVideo
from weboob.tools.backend import BaseBackend, ObjectNotAvailable
from weboob.tools.misc import to_unicode

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

    def get_video(self, _id):
        with self.browser:
            try:
                return self.browser.get_video(_id)
            except ForbiddenVideo, e:
                raise ObjectNotAvailable(e)

    def iter_search_results(self, pattern=None, sortby=ICapVideo.SEARCH_RELEVANCE, nsfw=False, max_results=None):
        import gdata.youtube.service

        YOUTUBE_MAX_RESULTS = 50
        YOUTUBE_MAX_START_INDEX = 1000
        yt_service = gdata.youtube.service.YouTubeService()

        start_index = 1
        nb_yielded = 0
        while True:
            query = gdata.youtube.service.YouTubeVideoQuery()
            if pattern is not None:
                query.vq = pattern
            query.orderby = ('relevance', 'rating', 'viewCount', 'published')[sortby]
            query.racy = 'include' if nsfw else 'exclude'

            if max_results is None or max_results > YOUTUBE_MAX_RESULTS:
                query_max_results = YOUTUBE_MAX_RESULTS
            else:
                query_max_results = max_results
            query.max_results = query_max_results

            if start_index > YOUTUBE_MAX_START_INDEX:
                return
            query.start_index = start_index
            start_index += query_max_results

            feed = yt_service.YouTubeQuery(query)
            for entry in feed.entry:
                video = YoutubeVideo(to_unicode(entry.id.text.split('/')[-1].strip()),
                                     title=to_unicode(entry.media.title.text.strip()),
                                     duration=to_unicode(datetime.timedelta(seconds=int(entry.media.duration.seconds.strip()))),
                                     thumbnail_url=to_unicode(entry.media.thumbnail[0].url.strip()),
                                     )
                if entry.media.name:
                    video.author = to_unicode(entry.media.name.text.strip())
                yield video
                nb_yielded += 1
                if nb_yielded == max_results:
                    return

    def fill_video(self, video, fields):
        if fields != ['thumbnail']:
            # if we don't want only the thumbnail, we probably want also every fields
            with self.browser:
                try:
                    video = self.browser.get_video(video.id, video)
                except ForbiddenVideo, e:
                    raise ObjectNotAvailable(e)
        if 'thumbnail' in fields:
            with self.browser:
                video.thumbnail.data = self.browser.readurl(video.thumbnail.url)
        return video

    OBJECTS = {YoutubeVideo: fill_video}
