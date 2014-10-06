# -*- coding: utf-8 -*-

# Copyright(C) 2013 Roger Philibert
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


import re

from weboob.capabilities.base import NotAvailable
from weboob.capabilities.image import BaseImage
from weboob.deprecated.browser import Page, BrokenPageError
from weboob.tools.misc import to_unicode

from .video import JacquieEtMichelVideo


class ResultsPage(Page):
    def iter_videos(self):
        for span in self.document.xpath('//ul[@id="list"]/li'):
            a = self.parser.select(span, 'a', 1)
            url = a.attrib['href']
            _id = re.sub(r'/showvideo/(\d+)/.*', r'\1', url)

            video = JacquieEtMichelVideo(_id)

            url = span.find('.//img').attrib['src']
            video.thumbnail = BaseImage(url)
            video.thumbnail.url = video.thumbnail.id

            title_el = self.parser.select(span, 'h2', 1)
            video.title = to_unicode(title_el.text.strip())
            video.description = self.parser.tocleanstring(span.xpath('.//div[@class="desc"]')[0])
            video.set_empty_fields(NotAvailable, ('url,'))

            yield video


class VideoPage(Page):
    def get_video(self, video=None):
        _id = to_unicode(self.group_dict['id'])
        if video is None:
            video = JacquieEtMichelVideo(_id)
        title_el = self.parser.select(self.document.getroot(), 'h1', 1)
        video.title = to_unicode(title_el.text.strip())
        video.description = self.document.xpath('//meta[@name="description"]')[0].attrib['content']

        for script in self.document.xpath('.//script'):
            if script.text is None:
                continue
            m = re.search('"(http://[^"]+.mp4)"', script.text, re.MULTILINE)
            if m:
                video.url = to_unicode(m.group(1))
                break

        if not video.url:
            raise BrokenPageError('Unable to find URL')

        video.set_empty_fields(NotAvailable)

        return video
