# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Christophe Benz, Romain Bignon
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


from __future__ import with_statement

import datetime
import gdata.youtube.service
import re
import urllib

from weboob.capabilities.video import ICapVideo
from weboob.tools.backend import BaseBackend
from weboob.tools.misc import to_unicode

from .browser import YoutubeBrowser
from .video import YoutubeVideo


__all__ = ['YoutubeBackend']


class YoutubeBackend(BaseBackend, ICapVideo):
    NAME = 'youtube'
    MAINTAINER = 'Christophe Benz'
    EMAIL = 'christophe.benz@gmail.com'
    VERSION = '0.9'
    DESCRIPTION = 'Youtube videos website'
    LICENSE = 'AGPLv3+'
    BROWSER = YoutubeBrowser

    URL_RE = re.compile(r'^https?://(?:\w*\.?youtube\.com/(?:watch\?v=|v/)|youtu\.be\/|\w*\.?youtube\.com\/user\/\w+#p\/u\/\d+\/)([^\?&]+)')
    AVAILABLE_FORMATS = [38, 37, 22, 45, 35, 34, 43, 18, 6, 5, 17, 13]
    FORMAT_EXTENSIONS = {
        13: '3gp',
        17: 'mp4',
        18: 'mp4',
        22: 'mp4',
        37: 'mp4',
        38: 'video', # You actually don't know if this will be MOV, AVI or whatever
        43: 'webm',
        45: 'webm',
    }

    def _entry2video(self, entry):
        """
        Parse an entry returned by gdata and return a Video object.
        """
        video = YoutubeVideo(to_unicode(entry.id.text.split('/')[-1].strip()),
                             title=to_unicode(entry.media.title.text.strip()),
                             duration=to_unicode(datetime.timedelta(seconds=int(entry.media.duration.seconds.strip()))),
                             thumbnail_url=to_unicode(entry.media.thumbnail[0].url.strip()),
                             )
        video.author = entry.author[0].name.text.strip()
        if entry.media.name:
            video.author = to_unicode(entry.media.name.text.strip())
        return video

    def _set_video_url(self, video, format=18):
        """
        In the case of a download, if the user-chosen format is not
        available, the next available format will be used.
        Much of the code for this method is borrowed from youtubeservice.py of Cutetube
        http://maemo.org/packages/view/cutetube/.
        """
        player_url = YoutubeVideo.id2url(video.id)
        html = urllib.urlopen(player_url).read()
        html = ''.join(html.split())
        formats = {}
        pos = html.find('","fmt_url_map":"')
        if (pos != -1):
            pos2 = html.find('"', pos + 17)
            fmt_map = urllib.unquote(html[pos + 17:pos2]) + ','
            parts = fmt_map.split('|')
            key = parts[0]
            for p in parts[1:]:
                idx = p.rfind(',')
                value = p[:idx].replace('\\/', '/').replace('\u0026', '&').replace(',', '%2C')
                formats[int(key)] = value
                key = p[idx + 1:]
        for format in self.AVAILABLE_FORMATS[self.AVAILABLE_FORMATS.index(format):]:
            if format in formats:
                video.url = formats.get(format)
                video.ext = self.FORMAT_EXTENSIONS.get(format, 'flv')
                return True

        return False

    def get_video(self, _id):
        m = self.URL_RE.match(_id)
        if m:
            _id = m.group(1)

        yt_service = gdata.youtube.service.YouTubeService()
        try:
            entry = yt_service.GetYouTubeVideoEntry(video_id=_id)
        except gdata.service.Error, e:
            if e.args[0]['status'] == 400:
                return None
            raise

        video = self._entry2video(entry)
        self._set_video_url(video)
        return video

    def iter_search_results(self, pattern=None, sortby=ICapVideo.SEARCH_RELEVANCE, nsfw=False, max_results=None):
        YOUTUBE_MAX_RESULTS = 50
        YOUTUBE_MAX_START_INDEX = 1000
        yt_service = gdata.youtube.service.YouTubeService()

        start_index = 1
        nb_yielded = 0
        while True:
            query = gdata.youtube.service.YouTubeVideoQuery()
            if pattern is not None:
                if isinstance(pattern, unicode):
                    pattern = pattern.encode('utf-8')
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
                yield self._entry2video(entry)
                nb_yielded += 1
                if nb_yielded == max_results:
                    return

    def fill_video(self, video, fields):
        if 'thumbnail' in fields:
            video.thumbnail.data = urllib.urlopen(video.thumbnail.url).read()
        if 'url' in fields:
            self._set_video_url(video)
        return video

    OBJECTS = {YoutubeVideo: fill_video}
