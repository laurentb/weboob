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


from weboob.browser import PagesBrowser, URL
from .pages import IndexPage, VideoPage

__all__ = ['PluzzBrowser']


class PluzzBrowser(PagesBrowser):
    ENCODING = 'utf-8'

    BASEURL = 'http://pluzz.francetv.fr'

    index_page = URL(r'recherche\?recherche=(?P<pattern>.*)', IndexPage)
    latest_page = URL(r'lesplusrecents', IndexPage)
    video_page = URL(r'http://webservices.francetelevisions.fr/tools/getInfosOeuvre/v2/\?idDiffusion=(?P<id>.*)&catalogue=Pluzz', VideoPage)

    def search_videos(self, pattern):
        return self.index_page.go(pattern=pattern).iter_videos()

    @video_page.id2url
    def get_video(self, url, video=None):
        self.location(url)
        video = self.page.get_video(obj=video)
        for item in self.read_url(video.url):
            video.url = u'%s' % item
        return video

    def read_url(self, url):
        r = self.open(url, stream=True)
        buf = r.iter_lines()
        r.close()
        return buf

    def latest_videos(self):
        return self.latest_page.go().iter_videos()
