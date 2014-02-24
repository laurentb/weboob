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


from datetime import datetime
import re

from weboob.capabilities import NotAvailable
from weboob.capabilities.image import BaseImage
from weboob.tools.browser import BasePage

from ..video import InaVideo

__all__ = ['VideoPage']


class VideoPage(BasePage):
    URL_REGEXP = re.compile('http://player.ina.fr/notices/(.+)\.mrss')

    def get_id(self):
        m = self.URL_REGEXP.match(self.url)
        if m:
            return m.group(1)
        self.logger.warning('Unable to parse ID')
        return 0

    def get_video(self, video):
        if not video:
            video = InaVideo(self.get_id())

        video.title = u'%s' % self.parser.select(self.document.getroot(),
                                                 '//rss/channel/item/title',
                                                 1,
                                                 method='xpath').text

        _image = u'%s' % self.parser.select(self.document.getroot(),
                                            '//rss/channel/item/media:content/media:thumbnail',
                                            1,
                                            method='xpath',
                                            namespaces={'media': 'http://search.yahoo.com/mrss/'}).attrib['url']
        video.thumbnail = BaseImage(_image)
        video.thumbnail.url = video.thumbnail.id

        video.url = u'%s' % self.parser.select(self.document.getroot(),
                                               '//rss/channel/item/media:content',
                                               1,
                                               method='xpath',
                                               namespaces={'media': 'http://search.yahoo.com/mrss/'}).attrib['url']

        _date = self.parser.select(self.document.getroot(),
                                   '//rss/channel/item/pubDate',
                                   1,
                                   method='xpath').text
        video.date = datetime.strptime(_date[:-6], '%a, %d %b %Y %H:%M:%S')


        video.description = u'%s' % self.parser.select(self.document.getroot(),
                                                       '//rss/channel/item/description',
                                                       1,
                                                       method='xpath').text

        video.set_empty_fields(NotAvailable)
        return video

    def get_title(self):
        qr = self.parser.select(self.document.getroot(), 'div.container-global-qr')[0]
        return unicode(qr.cssselect('h2.titre-propre')[0].text.strip())

    def get_description(self):
        desc = self.parser.select(self.document.getroot(), 'div.container-global-qr')[1].find('div').find('p')
        if desc:
            return unicode(desc.text.strip())
