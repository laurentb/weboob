# -*- coding: utf-8 -*-

# Copyright(C) 2010  Christophe Benz
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


import datetime
from logging import warning
import re
try:
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs

from weboob.tools.browser import BasePage
from weboob.tools.parsers.lxmlparser import SelectElementException

from ..video import InaVideo


__all__ = ['VideoPage']


class VideoPage(BasePage):
    URL_REGEXP = re.compile('http://boutique.ina.fr/video/(.+).html')

    def get_video(self, video):
        date, duration = self.get_date_and_duration()
        if not video:
            video = InaVideo(self.get_id())

        video.title = self.get_title()
        video.url = self.get_url()
        video.date = date
        video.duration = duration
        video.description = self.get_description()
        return video

    def get_id(self):
        m = self.URL_REGEXP.match(self.url)
        if m:
            return unicode(m.group(1))
        warning('Unable to parse ID')
        return 0

    def get_description(self):
        el = self.document.getroot().cssselect('div.bloc-produit-haut div.contenu p')[0]
        if el is not None:
            return el.text.strip()

    def get_date_and_duration(self):
        duration_regexp = re.compile('(.+) - ((.+)h)?((.+)min)?(.+)s')
        el = self.document.getroot().cssselect('div.bloc-produit-haut p.date')[0]
        if el is not None:
            m = duration_regexp.match(el.text.strip())
            if m:
                day, month, year = [int(s) for s in m.group(1).split('/')]
                date = datetime.datetime(year, month, day)
                duration = datetime.timedelta(hours=int(m.group(3) if m.group(3) is not None else 0),
                                              minutes=int(m.group(5) if m.group(5) is not None else 0),
                                              seconds=int(m.group(6)))
                return date, duration
            else:
                raise SelectElementException('Unable to parse date and duration')
        else:
            raise SelectElementException('Unable to find date and duration element')

    def get_title(self):
        el = self.document.getroot().cssselect('div.bloc-produit-haut h1')[0]
        if el is not None:
            return unicode(el.text.strip())
        else:
            return None

    def get_url(self):
        qs = parse_qs(self.document.getroot().cssselect('param[name="flashvars"]')[0].attrib['value'])
        url = 'http://mp4.ina.fr/lecture/lire/id_notice/%s/token_notice/%s' % (qs['id_notice'][0], qs['token_notice'][0])
        return url
