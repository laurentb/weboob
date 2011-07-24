# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Christophe Benz, Romain Bignon
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


from weboob.tools.browser import BaseBrowser

from .pages import ForbiddenVideoPage, VerifyAgePage, VideoPage


__all__ = ['YoutubeBrowser']


class YoutubeBrowser(BaseBrowser):
    DOMAIN = u'youtube.com'
    ENCODING = None
    PAGES = {r'.*youtube\.com/watch\?v=(?P<id>.+)': VideoPage,
             r'.*youtube\.com/index\?ytsession=.+': ForbiddenVideoPage,
             r'.*youtube\.com/verify_age\?next_url=(?P<next_url>.+)': VerifyAgePage,
            }

    def get_video_url(self, player_url):
        self.location(player_url)

        assert self.is_on_page(VideoPage)
        return self.page.get_video_url()
