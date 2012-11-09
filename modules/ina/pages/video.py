# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Christophe Benz
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
try:
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs

from weboob.capabilities import NotAvailable
from weboob.tools.browser import BasePage, BrokenPageError

from ..video import InaVideo


__all__ = ['VideoPage', 'BoutiqueVideoPage']


class BaseVideoPage(BasePage):
    def get_video(self, video):
        date, duration = self.get_date_and_duration()
        if not video:
            video = InaVideo(self.get_id())

        video.title = self.get_title()
        video.url = self.get_url()
        video.date = date
        video.duration = duration
        video.description = self.get_description()

        video.set_empty_fields(NotAvailable)
        return video

    def get_id(self):
        m = self.URL_REGEXP.match(self.url)
        if m:
            return self.create_id(m.group(1))
        self.logger.warning('Unable to parse ID')
        return 0

    def get_url(self):
        qs = parse_qs(self.document.getroot().cssselect('param[name="flashvars"]')[0].attrib['value'])
        s = self.browser.readurl('http://boutique.ina.fr/player/infovideo/id_notice/%s' % qs['id_notice'][0])
        s = s[s.find('<Media>')+7:s.find('</Media>')]
        return u'%s/pkey/%s' % (s, qs['pkey'][0])

    def parse_date_and_duration(self, text):
        duration_regexp = re.compile('(.* - )?(.+) - ((.+)h)?((.+)min)?(.+)s')
        m = duration_regexp.match(text)
        if m:
            day, month, year = [int(s) for s in m.group(2).split('/')]
            date = datetime.datetime(year, month, day)
            duration = datetime.timedelta(hours=int(m.group(4) if m.group(4) is not None else 0),
                                          minutes=int(m.group(6) if m.group(6) is not None else 0),
                                          seconds=int(m.group(7)))
            return date, duration
        else:
            raise BrokenPageError('Unable to parse date and duration')

    def create_id(self, id):
        raise NotImplementedError()

    def get_date_and_duration(self):
        raise NotImplementedError()

    def get_title(self):
        raise NotImplementedError()

    def get_description(self):
        raise NotImplementedError()

class VideoPage(BaseVideoPage):
    URL_REGEXP = re.compile('http://www.ina.fr/(.+)\.html')

    def create_id(self, id):
        return u'www.%s' % id

    def get_date_and_duration(self):
        qr = self.parser.select(self.document.getroot(), 'div.container-global-qr')[0].find('div').findall('div')[1]
        return self.parse_date_and_duration(qr.find('h2').tail.strip())

    def get_title(self):
        qr = self.parser.select(self.document.getroot(), 'div.container-global-qr')[0].find('div').findall('div')[1]
        return unicode(qr.find('h2').text.strip())

    def get_description(self):
        return unicode(self.parser.select(self.document.getroot(), 'div.container-global-qr')[1].find('div').find('p').text.strip())


class BoutiqueVideoPage(BaseVideoPage):
    URL_REGEXP = re.compile('http://boutique.ina.fr/(audio|video)/(.+).html')

    def create_id(self, id):
        return u'boutique.%s' % id

    def get_description(self):
        el = self.document.getroot().cssselect('div.bloc-produit-haut div.contenu p')[0]
        if el is not None:
            return unicode(el.text.strip())

    def get_date_and_duration(self):
        el = self.document.getroot().cssselect('div.bloc-produit-haut p.date')[0]
        if el is not None:
            return self.parse_date_and_duration(el.text.strip())
        else:
            raise BrokenPageError('Unable to find date and duration element')

    def get_title(self):
        el = self.document.getroot().cssselect('div.bloc-produit-haut h1')[0]
        if el is not None:
            return unicode(el.text.strip())
        else:
            return None
