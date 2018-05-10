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
from weboob.applications.suboob.suboob import LANGUAGE_CONV

from .pages import SubtitlesPage, SearchPage, SubtitlePage, SeriesSubtitlePage


__all__ = ['OpensubtitlesBrowser']


class OpensubtitlesBrowser(PagesBrowser):
    BASEURL = 'https://www.opensubtitles.org'
    search = URL('/en/search2/sublanguageid-(?P<language>.*)/moviename-(?P<movie>.*)(/offset-\d*)?', SearchPage)
    subtitles = URL('/en/search/sublanguageid-(?P<language>.*)/idmovie-(?P<id_movie>.*)',
                    '/en/search/imdbid-\d*/sublanguageid-(?P<language>.*)/moviename-(?P<movie>.*)', SubtitlesPage)
    subtitle = URL('/en/subtitles/(?P<id>.*)', SubtitlePage)
    series_subtitle = URL('/en/ssearch/sublanguageid-(?P<language>.*)/idmovie-(?P<id_movie>.*)', SeriesSubtitlePage)
    file = URL('/en/subtitleserve/sub/(?P<id>.+)')

    def iter_subtitles(self, language, pattern):
        lang = LANGUAGE_CONV[language]
        return self.search.go(language=lang, movie=pattern).iter_subtitles()

    def get_subtitle(self, id):
        return self.subtitle.go(id=id).get_subtitle(id)

    def get_file(self, id):
        return self.file.go(id=id).content
