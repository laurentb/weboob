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
from logging import warning

from weboob.tools.browser import BasePage

from ..video import YoutubeVideo


__all__ = ['VideoPage']


class VideoPage(BasePage):
    URL_REGEX = re.compile(r"https?://[w\.]*youtube.com/watch\?v=(.+)")
    VIDEO_SIGNATURE_REGEX = re.compile(r'&t=([^ ,&]*)')

    def on_loaded(self):
        self.video = YoutubeVideo(self.get_id())
        self.video.title = self.get_title()
        self.video.url = self.get_url()
        self.set_details(self.video)

    def get_id(self):
        m = self.URL_REGEX.match(self.url)
        if m:
            return m.group(1)
        warning("Unable to parse ID")
        return 0

    def get_url(self):
        video_signature = None
        for data in self.document.getiterator('script'):
            if not data.text:
                continue
            for m in re.finditer(self.VIDEO_SIGNATURE_REGEX, data.text):
                video_signature = m.group(1)
        return 'http://www.youtube.com/get_video?video_id=%s&t=%s&fmt=18' % (self.video.id, video_signature)

    def get_title(self):
        found = self.document.getroot().cssselect('meta[name=title]')
        if found:
            content = found[0].attrib['content']
            return unicode(content).strip()
        return u''

    def set_details(self, v):
        v.author = self.document.getroot().cssselect('a.watch-description-username strong')[0].text
