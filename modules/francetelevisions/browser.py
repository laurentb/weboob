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

from weboob.tools.browser2 import PagesBrowser, URL
from .pages import IndexPage, VideoPage

__all__ = ['PluzzBrowser']


class PluzzBrowser(PagesBrowser):
    ENCODING = 'utf-8'

    BASEURL = 'http://pluzz.francetv.fr'

    index_page = URL('recherche\?recherche=(?P<pattern>.*)', IndexPage)
    latest_page = URL('lesplusrecents', IndexPage)
    video_page = URL('http://webservices.francetelevisions.fr/tools/getInfosOeuvre/v2/\?idDiffusion=(?P<_id>.*)&catalogue=Pluzz', VideoPage)

    def search_videos(self, pattern):
        return self.index_page.go(pattern=pattern).iter_videos()

    def get_video(self, _id, video=None):
        return self.video_page.go(_id=_id).get_video(obj=video)

    def latest_videos(self):
        return self.latest_page.go().iter_videos()
