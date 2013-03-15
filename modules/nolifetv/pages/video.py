# -*- coding: utf-8 -*-

# Copyright(C) 2011 Romain Bignon
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


from hashlib import md5
import time
from dateutil.parser import parse as parse_dt
import urllib

from weboob.capabilities.base import NotAvailable, UserError
from weboob.tools.capabilities.thumbnail import Thumbnail
from weboob.tools.browser import BasePage, BrokenPageError
from weboob.tools.misc import to_unicode

from ..video import NolifeTVVideo


__all__ = ['VideoPage']


class ForbiddenVideo(UserError):
    pass


class VideoPage(BasePage):
    def get_video(self, video=None):
        _id = to_unicode(self.group_dict['id'])
        if video is None:
            video = NolifeTVVideo(_id)

        # Check if video is external.
        try:
            div = self.parser.select(self.document.getroot(), 'div#message_lien_ext', 1)
        except BrokenPageError:
            pass
        else:
            link = div.find('a').attrib['href']
            raise ForbiddenVideo('Video is only available here: %s' % link)

        meta = self.parser.select(self.document.getroot(), 'meta[property="og:title"]', 1)
        try:
            video.title = unicode(meta.attrib['content'])
        except BrokenPageError:
            video.title = NotAvailable

        meta = self.parser.select(self.document.getroot(), 'meta[property="og:description"]', 1)
        try:
            video.description = unicode(meta.attrib['content'])
        except BrokenPageError:
            video.description = NotAvailable

        meta = self.parser.select(self.document.getroot(), 'meta[property="og:image"]', 1)
        try:
            video.thumbnail = Thumbnail(unicode(meta.attrib['content']))
        except BrokenPageError:
            video.thumbnail = NotAvailable

        try:
            video.date = parse_dt(self.parser.select(div, 'div#infos_complementaires', 1).find('p').text.strip())
        except Exception:
            video.date = NotAvailable
        video.author = NotAvailable
        video.duration = NotAvailable
        video.rating = NotAvailable
        video.rating_max = NotAvailable

        if not video.url:
            skey, timestamp = self.genkey()
            self.browser.readurl('http://online.nolife-tv.com/_nlfplayer/api/api_player.php',
                                 'skey=%s&a=MD5&timestamp=%s' % (skey, timestamp))

            skey, timestamp = self.genkey()
            self.browser.readurl('http://online.nolife-tv.com/_nlfplayer/api/api_player.php',
                                 'a=EML&skey=%s&id%%5Fnlshow=%s&timestamp=%s' % (skey, _id, timestamp))

            skey, timestamp = self.genkey()
            data = self.browser.readurl('http://online.nolife-tv.com/_nlfplayer/api/api_player.php',
                                         'quality=0&a=UEM%%7CSEM%%7CMEM%%7CCH%%7CSWQ&skey=%s&id%%5Fnlshow=%s&timestamp=%s' % (skey, _id, timestamp))

            values = dict([urllib.splitvalue(s) for s in data.split('&')])

            if not 'url' in values:
                raise ForbiddenVideo(values.get('message', 'Not available').decode('iso-8859-15'))
            video.url = unicode(values['url'])

        video.set_empty_fields(NotAvailable)

        return video

    SALT = 'a53be1853770f0ebe0311d6993c7bcbe'

    def genkey(self):
        # This website is really useful to get info: http://www.showmycode.com/
        timestamp = str(int(time.time()))
        skey = md5(md5(timestamp).hexdigest() + self.SALT).hexdigest()
        return skey, timestamp
