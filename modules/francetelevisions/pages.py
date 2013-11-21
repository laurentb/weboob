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
from dateutil.parser import parse as parse_dt

from weboob.capabilities import UserError
from weboob.tools.capabilities.thumbnail import Thumbnail
from weboob.tools.browser import BasePage, BrokenPageError


from .video import PluzzVideo


__all__ = ['IndexPage', 'VideoPage']


class IndexPage(BasePage):
    def iter_videos(self):
        for div in self.parser.select(self.document.getroot(), 'article.rs-cell'):
            title = self.parser.select(div, 'h3 a', 1)
            url = title.attrib['href']
            m = re.match('^http://pluzz.francetv.fr/videos/(.+).html$', url)
            if not m:
                self.logger.debug('url %s does not match' % url)
                continue
            _id = m.group(1)
            video = PluzzVideo(_id)
            video.title = unicode(title.text.strip())
            for p in div.xpath('.//p[@class="bientot"]'):
                video.title += ' - %s' % p.text.split('|')[0].strip()
            video.date = parse_dt(div.find('span').attrib['data-date'])
            duration = div.xpath('.//span[@class="type-duree"]')[0].text.split('|')[1].strip()
            if duration[-1:] == "'":
                t = [0, int(duration[:-1])]
            else:
                t = map(int, duration.split(':'))
            video.duration = datetime.timedelta(hours=t[0], minutes=t[1])

            url = self.parser.select(div, 'a.vignette img', 1).attrib['src']
            video.thumbnail = Thumbnail(url)

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
                return r'http://pluzz.francetv.fr/appftv/webservices/video/getInfosOeuvre.php?mode=zeri&id-diffusion=%s' % m.group(1)

    def get_id(self):
        return self.groups[0]
