# -*- coding: utf-8 -*-

# Copyright(C) 2011-2012  Romain Bignon, Laurent Bachelier
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

from weboob.capabilities import UserError
from weboob.tools.capabilities.thumbnail import Thumbnail
from weboob.tools.browser import BasePage, BrokenPageError


from .video import PluzzVideo


__all__ = ['IndexPage', 'VideoPage']


class IndexPage(BasePage):
    def iter_videos(self):
        for div in self.parser.select(self.document.getroot(), 'li.vignette'):
            title = self.parser.select(div, 'h4 a', 1)
            url = title.attrib['href']
            m = re.match('^http://www.pluzz.fr/([^/]+)\.html$', url)
            if not m:
                self.logger.debug('url %s does not match' % url)
                continue
            _id = m.group(1)
            video = PluzzVideo(_id)
            m = re.match('^(.+) - ([0-2][0-9])h([0-5][0-9])$', title.text)
            if m:
                video.title = m.group(1)
                hour = int(m.group(2))
                minute = int(m.group(3))
            else:
                video.title = title.text
                hour = 0
                minute = 0

            m = re.match('(\d+)/(\d+)/(\d+)', self.parser.select(div, 'p.date', 1).text)
            if m:
                video.date = datetime.datetime(int(m.group(3)),
                                               int(m.group(2)),
                                               int(m.group(1)),
                                               hour,
                                               minute)

            url = self.parser.select(div, 'img.illustration', 1).attrib['src']
            video.thumbnail = Thumbnail(u'http://www.pluzz.fr/%s' % url)

            yield video


class VideoPage(BasePage):
    def on_loaded(self):
        p = self.parser.select(self.document.getroot(), 'p.alert')
        if len(p) > 0:
            raise UserError(p[0].text)

    def get_info_url(self):
        try:
            div = self.parser.select(self.document.getroot(), 'a#current_video', 1)
        except BrokenPageError:
            return None
        else:
            m = re.match(
                '^%s(\d+)$' % re.escape('http://info.francetelevisions.fr/?id-video='),
                div.attrib['href'])
            if m:
                return r'http://www.pluzz.fr/appftv/webservices/video/getInfosOeuvre.php?mode=zeri&id-diffusion=%s' % m.group(1)

    def get_id(self):
        return self.groups[0]
