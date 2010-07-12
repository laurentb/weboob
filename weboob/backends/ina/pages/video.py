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

from ..video import InaVideo


__all__ = ['VideoPage']


class VideoPage(BasePage):
    URL_REGEXP = re.compile('http://boutique.ina.fr/video/(.+).html')

    def on_loaded(self):
        date, duration = self.get_date_and_duration()
        self.video = InaVideo(self.get_id(),
                              title=self.get_title(),
                              url=self.get_url(),
                              date=date,
                              duration=duration,
                              )

    def get_id(self):
        m = self.URL_REGEXP.match(self.url)
        if m:
            return unicode(m.group(1))
        warning('Unable to parse ID')
        return 0

    def get_date_and_duration(self):
        duration_regexp = re.compile('(.+) - (.+)min(.+)s')
        el = self.document.getroot().cssselect('.bloc-video-edito h3')[0]
        if el is not None:
            m = duration_regexp.match(el.text.strip())
            if m:
                day, month, year = [int(s) for s in m.group(1).split('/')]
                date = datetime.datetime(year, month, day)
                duration = datetime.timedelta(minutes=m.group(3), seconds=m.group(2))
                return date, duration
        else:
            return None

    def get_title(self):
        el = self.document.getroot().cssselect('.bloc-video-edito h2')[0]
        if el is not None:
            return unicode(el.text.strip())
        else:
            return None

    def get_url(self):
        qs = parse_qs(self.document.getroot().cssselect('param[name="flashvars"]')[0].attrib['value'])
        url = 'http://mp4.ina.fr/lecture/lire/id_notice/%s/token_notice/%s' % (qs['id_notice'][0], qs['token_notice'][0])
        return url
