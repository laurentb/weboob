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

from .pages import SubtitlesPage, SearchPage, SubtitlePage


__all__ = ['OpensubtitlesBrowser']


class OpensubtitlesBrowser(BaseBrowser):
    DOMAIN = 'www.opensubtitles.org'
    PROTOCOL = 'http'
    ENCODING = 'utf-8'
    USER_AGENT = BaseBrowser.USER_AGENTS['wget']
    PAGES = {
        'http://www.opensubtitles.org.*search2/sublanguageid.*moviename.*': SearchPage,
        'http://www.opensubtitles.org.*search/sublanguageid.*idmovie.*': SubtitlesPage,
        'http://www.opensubtitles.org.*search/imdbid.*/sublanguageid.*/moviename.*' : SubtitlesPage,
        'http://www.opensubtitles.org.*subtitles/[0-9]*/.*' : SubtitlePage
        }
    LANGUAGE_CONV = {'fr':'fre','en':'eng'}

    def iter_subtitles(self, language, pattern):
        lang = self.LANGUAGE_CONV[language]
        self.location('http://www.opensubtitles.org/search2/sublanguageid-%s/moviename-%s' % (lang,pattern.encode('utf-8')))
        assert self.is_on_page(SearchPage) or self.is_on_page(SubtitlesPage) or self.is_on_page(SubtitlePage)
        return self.page.iter_subtitles()

    def get_subtitle(self, id):
        """ the id is formed this way : id_movie|id_file
        the id_movie helps to find the page
        the id_file help to find the file into the page
        if NO id_movie set, using id_file to form the URL
        """
        self.location('http://www.opensubtitles.org/subtitles/%s' % id)
        assert self.is_on_page(SubtitlePage)
        return self.page.get_subtitle()
