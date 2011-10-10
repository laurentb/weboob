# -*- coding: utf-8 -*-

# Copyright(C) 2011  Romain Bignon
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

import datetime
import re

from weboob.tools.capabilities.thumbnail import Thumbnail
from weboob.tools.browser import BasePage, BrokenPageError


from .video import PluzzVideo


__all__ = ['IndexPage', 'VideoPage']


class IndexPage(BasePage):
    def iter_videos(self):
        for div in self.parser.select(self.document.getroot(), 'li.vignette'):
            url = self.parser.select(div, 'h4 a', 1).attrib['href']
            m = re.match('http://www.pluzz.fr/([^/]+).html', url)
            if not m:
                print ':('
                continue
            _id = m.group(1)
            video = PluzzVideo(_id)
            video.title = self.parser.select(div, 'h4 a', 1).text
            m = re.match('(\d+)/(\d+)/(\d+)', self.parser.select(div, 'p.date', 1).text)
            if m:
                video.date = datetime.datetime(int(m.group(3)),
                                               int(m.group(2)),
                                               int(m.group(1)))
            url = self.parser.select(div, 'img.illustration', 1).attrib['src']
            video.thumbnail = Thumbnail('http://www.pluzz.fr/%s' % url)

            yield video

class VideoPage(BasePage):
    def on_loaded(self):
        p = self.parser.select(self.document.getroot(), 'p.alert')
        if len(p) > 0:
            raise Exception(p[0].text)

    def get_meta_url(self):
        try:
            div = self.parser.select(self.document.getroot(), 'a#current_video', 1)
        except BrokenPageError:
            return None
        else:
            return div.attrib['href']

    def get_id(self):
        return self.groups[0]

class MetaVideoPage(BasePage):
    def get_meta(self, name):
        return self.parser.select(self.document.getroot(), 'meta[name=%s]' % name, 1).attrib['content']

    def get_video(self, id, video=None):
        if video is None:
            video = PluzzVideo(id)

        video.title = self.get_meta('vignette-titre-court')
        video.url = 'mms://videozones.francetv.fr/%s' % self.get_meta('urls-url-video')[len('geoloc/'):]
        video.description = self.get_meta('description')
        hours, minutes, seconds = self.get_meta('vignette-duree').split(':')
        video.duration = datetime.timedelta(hours=int(hours), minutes=int(minutes), seconds=int(seconds))

        return video
