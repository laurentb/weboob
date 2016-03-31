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


import re
import urllib

from weboob.capabilities.base import NotAvailable
from weboob.capabilities.image import Thumbnail
from weboob.capabilities.video import CapVideo, BaseVideo
from weboob.capabilities.collection import CapCollection, CollectionNotFound
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.misc import to_unicode
from weboob.tools.value import ValueBackendPassword, Value

from .browser import YoutubeBrowser
from .video import YoutubeVideo

try:
    # weboob modifies HTTPSConnection, which conflicts with apiclient
    # so apiclient must be imported after
    from apiclient.discovery import build as ytbuild
except ImportError:
    raise ImportError("Please install python-googleapi")

__all__ = ['YoutubeModule']


class YoutubeModule(Module, CapVideo, CapCollection):
    NAME = 'youtube'
    MAINTAINER = u'Laurent Bachelier'
    EMAIL = 'laurent@bachelier.name'
    VERSION = '1.2'
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
        Parse an entry returned by googleapi and return a Video object.
        """
        snippet = entry['snippet']
        video = YoutubeVideo(to_unicode(entry['id']['videoId']))
        video.title = to_unicode(snippet['title'].strip())
        # duration does not seem to be available with api
        video.thumbnail = Thumbnail(snippet['thumbnails']['default']['url'])
        video.author = to_unicode(snippet['channelTitle'].strip())
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

        params = {'id': _id, 'part': 'id,snippet'}

        youtube = self._build_yt()
        response = youtube.videos().list(**params).execute()
        items = response.get('items', [])
        if not items:
            return None

        video = self._entry2video(items[0])
        self._set_video_url(video)

        video.set_empty_fields(NotAvailable)

        # Youtube video url is https, using ssl encryption
        # so we need to use the "play_proxy" method using urllib2 proxy streaming to handle this
        video._play_proxy = True

        return video

    def _build_yt(self):
        DEVELOPER_KEY = "AIzaSyApVVeZ03XkKDYHX8T5uOn8Eizfe9CMDbs"
        YOUTUBE_API_SERVICE_NAME = "youtube"
        YOUTUBE_API_VERSION = "v3"

        return ytbuild(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
            developerKey=DEVELOPER_KEY)

    def search_videos(self, pattern, sortby=CapVideo.SEARCH_RELEVANCE, nsfw=False):
        YOUTUBE_MAX_RESULTS = 50

        youtube = self._build_yt()

        params = {'part': 'id,snippet', 'maxResults': YOUTUBE_MAX_RESULTS}
        if pattern is not None:
            if isinstance(pattern, unicode):
                pattern = pattern.encode('utf-8')
            params['q'] = pattern
        params['safeSearch'] = 'none' if nsfw else 'strict' # or 'moderate'
        params['order'] = ('relevance', 'rating', 'viewCount', 'date')[sortby]

        nb_yielded = 0
        while True:
            search_response = youtube.search().list(**params).execute()
            items = search_response.get('items', [])
            for entry in items:
                if entry["id"]["kind"] != "youtube#video":
                    continue
                yield self._entry2video(entry)
                nb_yielded += 1

            params['pageToken'] = search_response.get('nextPageToken')
            if not params['pageToken']:
                return
            if nb_yielded < YOUTUBE_MAX_RESULTS:
                return

    def latest_videos(self):
        return self.search_videos(None, CapVideo.SEARCH_DATE)

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
