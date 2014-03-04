# -*- coding: utf-8 -*-

# Copyright(C) 2010-2013 Christophe Benz, Romain Bignon, Laurent Bachelier
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




try:
    import gdata.youtube.service
except ImportError:
    raise ImportError("Please install python-gdata")

import datetime
import re
import urllib

from weboob.capabilities.base import NotAvailable
from weboob.capabilities.image import BaseImage
from weboob.capabilities.video import ICapVideo, BaseVideo
from weboob.capabilities.collection import ICapCollection, CollectionNotFound
from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.tools.misc import to_unicode
from weboob.tools.value import ValueBackendPassword, Value

from .browser import YoutubeBrowser
from .video import YoutubeVideo


__all__ = ['YoutubeBackend']


class YoutubeBackend(BaseBackend, ICapVideo, ICapCollection):
    NAME = 'youtube'
    MAINTAINER = u'Laurent Bachelier'
    EMAIL = 'laurent@bachelier.name'
    VERSION = '0.i'
    DESCRIPTION = 'YouTube video streaming website'
    LICENSE = 'AGPLv3+'
    BROWSER = YoutubeBrowser
    CONFIG = BackendConfig(Value('username', label='Email address', default=''),
                           ValueBackendPassword('password', label='Password', default=''))

    URL_RE = re.compile(r'^https?://(?:\w*\.?youtube(?:|-nocookie)\.com/(?:watch\?v=|embed/|v/)|youtu\.be\/|\w*\.?youtube\.com\/user\/\w+#p\/u\/\d+\/)([^\?&]+)')

    def create_default_browser(self):
        password = None
        username = self.config['username'].get()
        if len(username) > 0:
            password = self.config['password'].get()
        return self.create_browser(username, password)

    def _entry2video(self, entry):
        """
        Parse an entry returned by gdata and return a Video object.
        """
        video = YoutubeVideo(to_unicode(entry.id.text.split('/')[-1].strip()))
        video.title = to_unicode(entry.media.title.text.strip())
        video.duration = datetime.timedelta(seconds=int(entry.media.duration.seconds.strip()))
        video.thumbnail = BaseImage(entry.media.thumbnail[0].url.strip())
        video.thumbnail.url = to_unicode(video.thumbnail.id)

        if entry.author[0].name.text:
            video.author = to_unicode(entry.author[0].name.text.strip())
        if entry.media.name:
            video.author = to_unicode(entry.media.name.text.strip())
        return video

    def _set_video_url(self, video):
        """
        In the case of a download, if the user-chosen format is not
        available, the next available format will be used.
        Much of the code for this method is borrowed from youtubeservice.py of Cutetube
        http://maemo.org/packages/view/cutetube/.
        """
        if video.url:
            return

        player_url = YoutubeVideo.id2url(video.id)
        with self.browser:
            url, ext = self.browser.get_video_url(video, player_url)

        video.url = unicode(url)
        video.ext = unicode(ext)

    def get_video(self, _id):
        m = self.URL_RE.match(_id)
        if m:
            _id = m.group(1)

        yt_service = gdata.youtube.service.YouTubeService()
        yt_service.ssl = True
        try:
            entry = yt_service.GetYouTubeVideoEntry(video_id=_id)
        except gdata.service.Error as e:
            if e.args[0]['status'] == 400:
                return None
            raise

        video = self._entry2video(entry)
        self._set_video_url(video)

        video.set_empty_fields(NotAvailable)
        return video

    def search_videos(self, pattern, sortby=ICapVideo.SEARCH_RELEVANCE, nsfw=False):
        YOUTUBE_MAX_RESULTS = 50
        YOUTUBE_MAX_START_INDEX = 500
        yt_service = gdata.youtube.service.YouTubeService()
        yt_service.ssl = True

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

            query.max_results = YOUTUBE_MAX_RESULTS
            if start_index >= YOUTUBE_MAX_START_INDEX:
                return
            query.start_index = start_index
            start_index += YOUTUBE_MAX_RESULTS

            feed = yt_service.YouTubeQuery(query)
            for entry in feed.entry:
                yield self._entry2video(entry)
                nb_yielded += 1

            if nb_yielded < YOUTUBE_MAX_RESULTS:
                return

    def latest_videos(self):
        return self.search_videos(None, ICapVideo.SEARCH_DATE)

    def fill_video(self, video, fields):
        if 'thumbnail' in fields:
            video.thumbnail.data = urllib.urlopen(video.thumbnail.url).read()
        if 'url' in fields:
            self._set_video_url(video)
        return video

    def iter_resources(self, objs, split_path):
        if BaseVideo in objs:
            collection = self.get_collection(objs, split_path)
            if collection.path_level == 0:
                yield self.get_collection(objs, [u'latest'])
            if collection.split_path == [u'latest']:
                for video in self.latest_videos():
                    yield video

    def validate_collection(self, objs, collection):
        if collection.path_level == 0:
            return
        if BaseVideo in objs and collection.split_path == [u'latest']:
            collection.title = u'Latest YouTube videos'
            return
        raise CollectionNotFound(collection.split_path)

    OBJECTS = {YoutubeVideo: fill_video}
