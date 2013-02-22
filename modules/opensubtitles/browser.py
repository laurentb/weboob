# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Julien Veyssier
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

from .pages import SubtitlesPage, SearchPage


__all__ = ['OpensubtitlesBrowser']


class OpensubtitlesBrowser(BaseBrowser):
    DOMAIN = 'www.opensubtitles.org'
    PROTOCOL = 'http'
    ENCODING = 'utf-8'
    USER_AGENT = BaseBrowser.USER_AGENTS['wget']
    PAGES = {
        'http://www.opensubtitles.org.*search2/sublanguageid.*moviename.*': SearchPage,
        'http://www.opensubtitles.org.*search/sublanguageid.*idmovie.*': SubtitlesPage,
        'http://www.opensubtitles.org.*search/imdbid.*/sublanguageid.*/moviename.*' : SubtitlesPage
        }
    LANGUAGE_CONV = {'fr':'fre','en':'eng'}

    def iter_subtitles(self, language, pattern):
        lang = self.LANGUAGE_CONV[language]
        self.location('http://www.opensubtitles.org/search2/sublanguageid-%s/moviename-%s' % (lang,pattern.encode('utf-8')))
        assert self.is_on_page(SearchPage) or self.is_on_page(SubtitlesPage)
        return self.page.iter_subtitles(language,pattern)

    def get_subtitle(self, id):
        ids = id.split('|')
        id_movie = ids[0]
        id_file = ids[1]
        self.location('http://www.opensubtitles.org/search/sublanguageid-all/idmovie-%s' % id_movie)
        assert self.is_on_page(SubtitlesPage)
        return self.page.get_subtitle(id_file)
