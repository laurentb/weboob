# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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
import urllib

from weboob.tools.browser import BasePage, BrokenPageError
from weboob.tools.capabilities.thumbnail import Thumbnail
from weboob.capabilities import NotAvailable


from .video import ArteVideo


__all__ = ['IndexPage', 'VideoPage']


class IndexPage(BasePage):
    def iter_videos(self):
        videos = self.document.getroot().cssselect("div[class=video]")
        for div in videos:
            title = div.find('h2').find('a').text
            m = re.match(r'/fr/videos/(.*)\.html', div.find('h2').find('a').attrib['href'])
            _id = ''
            if m:
                _id = m.group(1)
            rating = rating_max = 0
            rates = self.parser.select(div, 'div[class=rateContainer]', 1)
            for r in rates.findall('div'):
                if 'star-rating-on' in r.attrib['class']:
                    rating += 1
                rating_max += 1

            video = ArteVideo(_id)
            video.title = title
            video.rating = rating
            video.rating_max = rating_max

            thumb = self.parser.select(div, 'img[class=thumbnail]', 1)
            video.thumbnail = Thumbnail('http://videos.arte.tv' + thumb.attrib['src'])

            try:
                parts = self.parser.select(div, 'div.duration_thumbnail', 1).text.split(':')
                if len(parts) == 2:
                    hours = 0
                    minutes, seconds = parts
                elif len(parts) == 3:
                    hours, minutes, seconds = parts
                else:
                    raise BrokenPageError('Unable to parse duration %r' % parts)
            except BrokenPageError:
                pass
            else:
                video.duration = datetime.timedelta(hours=int(hours), minutes=int(minutes), seconds=int(seconds))

            video.set_empty_fields(NotAvailable, ('url',))

            yield video

class VideoPage(BasePage):
    def get_video(self, video=None, lang='fr', quality='hd'):
        if not video:
            video = ArteVideo(self.group_dict['id'])
        video.title = self.get_title()
        video.url = self.get_url(lang, quality)
        video.set_empty_fields(NotAvailable)
        return video

    def get_title(self):
        return self.document.getroot().cssselect('h2')[0].text

    def get_url(self, lang, quality):
        obj = self.parser.select(self.document.getroot(), 'object', 1)
        movie_url = self.parser.select(obj, 'param[name=movie]', 1)
        xml_url = urllib.unquote(movie_url.attrib['value'].split('videorefFileUrl=')[-1])

        doc = self.browser.get_document(self.browser.openurl(xml_url))
        videos_list = self.parser.select(doc.getroot(), 'video')
        videos = {}
        for v in videos_list:
            videos[v.attrib['lang']] = v.attrib['ref']

        if lang in videos:
            xml_url = videos[lang]
        else:
            xml_url = videos.popitem()[1]

        doc = self.browser.get_document(self.browser.openurl(xml_url))

        obj = self.parser.select(doc.getroot(), 'urls', 1)
        videos_list = self.parser.select(obj, 'url')
        urls = {}
        for v in videos_list:
            urls[v.attrib['quality']] = v.text

        if quality in urls:
            video_url = urls[quality]
        else:
            video_url = urls.popitem()[1]

        return video_url
