# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Nicolas Duhamel, Laurent Bachelier
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

import requests
import urllib

import lxml.etree

from weboob.deprecated.browser import Browser
from weboob.deprecated.browser.decorators import id2url

from .pages import ChannelsPage, VideoPage
from .video import CanalplusVideo

from weboob.capabilities.collection import CollectionNotFound

__all__ = ['CanalplusBrowser']


class XMLParser(object):
    def parse(self, data, encoding=None):
        if encoding is None:
            parser = None
        else:
            parser = lxml.etree.XMLParser(encoding=encoding, strip_cdata=False)
        return lxml.etree.XML(data.get_data(), parser)


class CanalplusBrowser(Browser):
    DOMAIN = u'service.canal-plus.com'
    ENCODING = 'utf-8'
    PAGES = {
        r'http://service.canal-plus.com/video/rest/initPlayer/cplus/': ChannelsPage,
        r'http://service.canal-plus.com/video/rest/search/cplus/.*': VideoPage,
        r'http://service.canal-plus.com/video/rest/getVideosLiees/cplus/(?P<id>.+)': VideoPage,
        r'http://service.canal-plus.com/video/rest/getMEAs/cplus/.*': VideoPage,
        }

    #We need lxml.etree.XMLParser to read CDATA
    PARSER = XMLParser()
    FORMATS = {
        'sd': 0,
        'hd': -1,
        }

    def __init__(self, quality, *args, **kwargs):
        Browser.__init__(self, parser=self.PARSER, *args, **kwargs)
        self.quality = self.FORMATS.get(quality, self.FORMATS['hd'])

    def home(self):
        self.location('http://service.canal-plus.com/video/rest/initPlayer/cplus/')

    def search_videos(self, pattern):
        self.location('http://service.canal-plus.com/video/rest/search/cplus/' + urllib.quote_plus(pattern.replace('/', '').encode('utf-8')))
        return self.page.iter_results()

    @id2url(CanalplusVideo.id2url)
    def get_video(self, url, video=None):
        self.location(url)
        video = self.page.get_video(video)
        video.url = u'%s' % self.read_url(video.url)[self.quality]
        return video

    def read_url(self, url):
        r = requests.get(url, stream=True)
        buf = r.iter_lines()
        return [line for line in buf if not line.startswith('#')]

    def iter_resources(self, split_path):
        if not self.is_on_page(ChannelsPage):
            self.home()
        channels = self.page.get_channels()

        if len(split_path) == 0:
            for channel in channels:
                if channel.path_level == 1:
                    yield channel
        elif len(split_path) == 1:
            for channel in channels:
                if channel.path_level == 2 and split_path == channel.parent_path:
                    yield channel
        elif len(split_path) == 2:
            subchannels = self.iter_resources(split_path[0:1])
            try:
                channel = [subchannel for subchannel in subchannels
                           if split_path == subchannel.split_path][0]
                self.location("http://service.canal-plus.com/video/rest/getMEAs/cplus/%s" % channel._link_id)
                assert self.is_on_page(VideoPage)
                for video in self.page.iter_channel():
                    yield video
            except IndexError:
                raise CollectionNotFound(split_path)
        else:
            raise CollectionNotFound(split_path)
