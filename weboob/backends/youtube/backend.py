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
import gdata.youtube.service
import re
import urllib

from weboob.capabilities.video import ICapVideo
from weboob.tools.backend import BaseBackend
from weboob.tools.misc import to_unicode

from .browser import YoutubeBrowser
from .video import YoutubeVideo


__all__ = ['YoutubeBackend']


def get_video(entry):
    video = YoutubeVideo(to_unicode(entry.id.text.split('/')[-1].strip()),
                         title=to_unicode(entry.media.title.text.strip()),
                         duration=to_unicode(datetime.timedelta(seconds=int(entry.media.duration.seconds.strip()))),
                         thumbnail_url=to_unicode(entry.media.thumbnail[0].url.strip()),
                         )
    video.author = entry.author[0].name.text.strip()
    if entry.media.name:
        video.author = to_unicode(entry.media.name.text.strip())
    return video


def get_video_url(video, format=18):
    """
    Returns the YouTube video url for download or playback.
    In the case of a download, if the user-chosen format is not
    available, the next available format will be used.
    Much of the code for this method is borrowed from youtubeservice.py of Cutetube
    http://maemo.org/packages/view/cutetube/.
    """
    video_url = ''
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
            value = p[:idx].replace('\\/', '/')
            formats[int(key)] = value
            key = p[idx + 1:]
    format_list = [22, 35, 34, 18, 17]
    for format in format_list[format_list.index(format):]:
        if format in formats:
            video_url = formats.get(format)
            break
        break
    return video_url


class YoutubeBackend(BaseBackend, ICapVideo):
    NAME = 'youtube'
    MAINTAINER = 'Christophe Benz'
    EMAIL = 'christophe.benz@gmail.com'
    VERSION = '0.7'
    DESCRIPTION = 'Youtube videos website'
    LICENSE = 'GPLv3'
    BROWSER = YoutubeBrowser

    URL_RE = re.compile(r'https?://.*youtube.com/watch\?v=(.*)')

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

        video = get_video(entry)
        video.url = get_video_url(video)
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
                yield get_video(entry)
                nb_yielded += 1
                if nb_yielded == max_results:
                    return

    def fill_video(self, video, fields):
        if 'thumbnail' in fields:
            video.thumbnail.data = urllib.urlopen(video.thumbnail.url).read()
        if 'url' in fields:
            video.url = get_video_url(video)
        return video

    OBJECTS = {YoutubeVideo: fill_video}
