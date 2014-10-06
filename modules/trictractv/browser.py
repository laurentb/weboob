# -*- coding: utf-8 -*-

# Copyright(C) 2011-2012  Romain Bignon, Laurent Bachelier, Benjamin Drieu
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

from weboob.deprecated.browser import Browser
from weboob.deprecated.browser.decorators import id2url

from .pages import IndexPage, VideoPage
from .video import TricTracTVVideo


__all__ = ['TricTracTVBrowser']


class TricTracTVBrowser(Browser):
    DOMAIN = 'trictrac.tv'
    ENCODING = 'ISO-8859-1'
    PAGES = {r'http://[w\.]*trictrac.tv/': IndexPage,
             r'http://[w\.]*trictrac.tv/home/listing.php.*': IndexPage,
             r'http://[w\.]*trictrac.tv/video-(.+)': VideoPage,
            }

    @id2url(TricTracTVVideo.id2url)
    def get_video(self, url, video=None):
        self.location(url)
        assert self.is_on_page(VideoPage)

        _id = self.page.get_id()
        if video is None:
            video = TricTracTVVideo(_id)

        infourl = self.page.get_info_url()
        if infourl is not None:
            self.parse_info(self.openurl(infourl).read(), video)

        return video

    def home(self):
        self.location(self.buildurl('http://www.trictrac.tv/home/listing.php', mot='%'))

    def search_videos(self, pattern):
        if not pattern:
            self.home()
        else:
            self.location(self.buildurl('http://www.trictrac.tv/home/listing.php', mot=pattern.encode('utf-8')))

        assert self.is_on_page(IndexPage)
        return self.page.iter_videos()

    def parse_info(self, data, video):
        m = re.match ( '.*fichier=(.*?)&', data )
        video.url = unicode ( r'http://src.povcon.net/videos/%s' % m.group ( 1 ) )

        video.description = self.page.get_descriptif()
        video.duration = self.page.get_duration()
        video.title = self.page.get_title()
        video.date = self.page.get_date()
        video.rating = self.page.get_rating()
        video.rating_max = 5

        return video
