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

from weboob.capabilities.image import BaseImage
from weboob.deprecated.browser import Page, BrokenPageError


from .video import TricTracTVVideo


class IndexPage(Page):
    def iter_videos(self):
        for div in self.parser.select(self.document.getroot(), 'li#contentsearch'):
            title = self.parser.select(div, '#titlesearch span', 1)

            a = self.parser.select(div, 'a', 1)
            url = a.attrib['href']
            m = re.match('/video-(.*)', url)
            if not m:
                self.logger.debug('url %s does not match' % url)
                continue
            _id = m.group(1)
            video = TricTracTVVideo(_id)
            video.title = unicode(title.text)

            url = self.parser.select(div, 'img', 1).attrib['src']
            stars = self.parser.select(div, '.etoile_on')
            video.rating = len(stars)
            video.rating_max = 5

            video.thumbnail = BaseImage('http://www.trictrac.tv/%s' % url)
            video.thumbnail.url = video.thumbnail.id

            yield video


class VideoPage(Page):
    def on_loaded(self):
        p = self.parser.select(self.document.getroot(), 'p.alert')
        if len(p) > 0:
            raise Exception(p[0].text)

    def get_info_url(self):
        try:
            div = self.parser.select(self.document.getroot(), '#Content_Video object', 1)
        except BrokenPageError:
            return None
        else:
            for param in self.parser.select(div, 'param', None):
                if param.get('name') == 'flashvars':
                    m = re.match('varplaymedia=([0-9]*)', param.attrib['value'])
                    if m:
                        return r'http://www.trictrac.tv/swf/listelement.php?idfile=%s' % m.group(1)

    def get_title(self):
        try:
            title = self.parser.select(self.document.getroot(), 'title', 1)
        except BrokenPageError:
            return None
        else:
            return title.text

    def get_descriptif(self):
        try:
            descriptif = self.parser.select(self.document.getroot(), '.video_descriptif p', 1)
        except BrokenPageError:
            return None
        else:
            return descriptif.text

    def get_duration(self):
        try:
            details = self.parser.select(self.document.getroot(), 'div#video_detail div')
        except BrokenPageError:
            return None
        else:
            duration = details[2]
            duration_string = duration.text [ duration.text.rfind ( ' ' ) + 1 : ]
            tokens = duration_string.split(':')
            if len(tokens) > 2:
                return datetime.timedelta(hours=int(tokens[0]), minutes=int(tokens[1]), seconds=int(tokens[2]))
            else:
                return datetime.timedelta(minutes=int(tokens[0]), seconds=int(tokens[1]))

    def get_date(self):
        try:
            date = self.parser.select(self.document.getroot(), 'div#video_detail div.date', 1)
        except BrokenPageError:
            return None
        else:
            string = date.text
            string = string [ string.rfind('le ') + 3 : ]
            months = [ 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec' ]
            words = string.split ( ' ' )
            month_no = months.index ( words [ 1 ] ) + 1
            return datetime.datetime.strptime ( ( '%s %s %s %s' %
                                                  ( words [ 0 ], month_no, words [ 2 ], words [ 3 ] ) ),
                                                '%d %m %Y, %H:%M:%S')

    def get_rating(self):
        try:
            stars = self.parser.select(self.document.getroot(), '#video_info .etoile_on')
        except BrokenPageError:
            return None
        else:
            return len(stars)

    def get_id(self):
        return self.groups[0]
