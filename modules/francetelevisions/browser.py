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

from __future__ import unicode_literals

from weboob.browser import PagesBrowser, URL
from weboob.exceptions import BrowserHTTPNotFound

from .pages import SearchPage, VideoWebPage, VideoJsonPage

__all__ = ['PluzzBrowser']


class PluzzBrowser(PagesBrowser):
    BASEURL = 'https://www.france.tv'
    PROGRAMS = None

    search_page = URL(r'/recherche/', SearchPage)
    video = URL(r'/.+/(?P<number>\d+)-[^/]+.html$', VideoWebPage)
    video_json = URL(r'https://sivideo.webservices.francetelevisions.fr/tools/getInfosOeuvre/v2/\?idDiffusion=(?P<number>.+)$', VideoJsonPage)

    def search_videos(self, s):
        self.location(self.search_page.build(), params={'q': s})
        return self.page.iter_videos()

    def get_video(self, id):
        self.location(id)
        number = self.page.get_number()

        try:
            self.video_json.go(number=number)
        except BrowserHTTPNotFound:
            self.logger.warning('video info not found, probably needs payment')
            return
        video = self.page.get_video()
        if not video:
            self.logger.debug('video info not found, maybe not available?')
            return
        video.id = id

        return video
