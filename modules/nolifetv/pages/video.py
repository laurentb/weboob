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

        div = self.parser.select(self.document.getroot(), 'div#informations_video', 1)
        video.title = self.parser.select(div, 'div#ligne_titre_big', 1).text
        try:
            video.description = self.parser.select(div, 'div#ligne_titre_small', 1).text
        except BrokenPageError:
            video.description = NotAvailable

        video.thumbnail = Thumbnail(self.parser.select(div, 'div#icone_video img', 1).attrib['src'])
        try:
            video.date = parse_dt(self.parser.select(div, 'div#infos_complementaires', 1).find('p').text.strip())
        except Exception:
            video.date = NotAvailable
        video.author = NotAvailable
        video.duration = NotAvailable
        video.rating = NotAvailable
        video.rating_max = NotAvailable

        if not video.url:
            r = self.browser.request_class('http://online.nolife-tv.com/_newplayer/api/api_player.php',
                                   'skey=9fJhXtl%5D%7CFR%3FN%7D%5B%3A%5Fd%22%5F&connect=1&a=US',
                                   {'Referer': 'http://online.nolife-tv.com/_newplayer/nolifeplayer_flash10.swf?idvideo=%s&autostart=0' % _id})
            self.browser.openurl(r)
            r = self.browser.request_class('http://online.nolife-tv.com/_newplayer/api/api_player.php',
                                   'skey=9fJhXtl%5D%7CFR%3FN%7D%5B%3A%5Fd%22%5F&a=UEM%7CSEM&quality=0&id%5Fnlshow=' + _id,
                                   {'Referer': 'http://online.nolife-tv.com/_newplayer/nolifeplayer_flash10.swf?idvideo=%s&autostart=0' % _id})
            data = self.browser.readurl(r)
            values = dict([urllib.splitvalue(s) for s in data.split('&')])

            if not 'url' in values:
                raise ForbiddenVideo(values.get('message', 'Not available').decode('iso-8859-15'))
            video.url = values['url']

        video.set_empty_fields(NotAvailable)

        return video
