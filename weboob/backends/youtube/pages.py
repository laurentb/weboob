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


import re

from weboob.tools.browser import BasePage
from weboob.tools.parsers.lxmlparser import select

from .video import YoutubeVideo


__all__ = ['ForbiddenVideoPage', 'VerifyAgePage', 'VideoPage']


class ForbiddenVideo(Exception):
    pass


class ForbiddenVideoPage(BasePage):
    def on_loaded(self):
        element = select(self.document.getroot(), '.yt-alert-content', 1)
        raise ForbiddenVideo(element.text.strip())


class VerifyAgePage(BasePage):
    def on_loaded(self):
        raise ForbiddenVideo('verify age not implemented')


class VideoPage(BasePage):
    VIDEO_SIGNATURE_REGEX = re.compile(r'&t=([^ ,&]*)')

    def on_loaded(self):
        _id = self.group_dict['id']
        self.video = YoutubeVideo(_id,
                                  title=self.get_title(),
                                  url=self.get_url(_id),
                                  author=self.get_author(),
                                  )

    def get_author(self):
        element = select(self.document.getroot(), 'a.watch-description-username strong', 1)
        return element.text.strip()

    def get_title(self):
        element = select(self.document.getroot(), 'meta[name=title]', 1)
        return unicode(element.attrib['content']).strip()

    def get_url(self, _id):
        video_signature = None
        for data in self.document.getiterator('script'):
            if not data.text:
                continue
            for m in re.finditer(self.VIDEO_SIGNATURE_REGEX, data.text):
                video_signature = m.group(1)
        return u'http://www.youtube.com/get_video?video_id=%s&t=%s&fmt=18' % (_id, video_signature)
