# -*- coding: utf-8 -*-

# Copyright(C) 2013 Julien Veyssier
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
from .pages import SearchPage, SubtitlePage


__all__ = ['PodnapisiBrowser']


class PodnapisiBrowser(PagesBrowser):
    BASEURL = 'https://www.podnapisi.net'
    search = URL('/subtitles/search/advanced\?keywords=(?P<keywords>.*)&language=(?P<language>.*)',
                 '/en/subtitles/search/advanced\?keywords=(?P<keywords>.*)&language=(?P<language>.*)',
                 SearchPage)
    file = URL('/subtitles/(?P<id>-*\w*)/download')
    subtitle = URL('/subtitles/(?P<id>.*)', SubtitlePage)

    def iter_subtitles(self, language, pattern):
        return self.search.go(language=language, keywords=pattern).iter_subtitles()

    def get_file(self, id):
        return self.file.go(id=id).content

    def get_subtitle(self, id):
        return self.subtitle.go(id=id).get_subtitle()
