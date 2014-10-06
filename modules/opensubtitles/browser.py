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


from weboob.deprecated.browser import Browser, BrowserHTTPNotFound
from weboob.applications.suboob.suboob import LANGUAGE_CONV

from .pages import SubtitlesPage, SearchPage, SubtitlePage


__all__ = ['OpensubtitlesBrowser']


class OpensubtitlesBrowser(Browser):
    DOMAIN = 'www.opensubtitles.org'
    PROTOCOL = 'http'
    ENCODING = 'utf-8'
    USER_AGENT = Browser.USER_AGENTS['wget']
    PAGES = {
        'http://www.opensubtitles.org.*search2/sublanguageid.*moviename.*': SearchPage,
        'http://www.opensubtitles.org.*search/sublanguageid.*idmovie.*': SubtitlesPage,
        'http://www.opensubtitles.org.*search/imdbid.*/sublanguageid.*/moviename.*': SubtitlesPage,
        'http://www.opensubtitles.org.*subtitles/[0-9]*/.*': SubtitlePage
    }

    def iter_subtitles(self, language, pattern):
        lang = LANGUAGE_CONV[language]
        self.location('http://www.opensubtitles.org/search2/sublanguageid-%s/moviename-%s' % (
            lang, pattern.encode('utf-8')))
        assert self.is_on_page(SearchPage) or self.is_on_page(SubtitlesPage) or self.is_on_page(SubtitlePage)
        return self.page.iter_subtitles()

    def get_subtitle(self, id):
        try:
            self.location('http://www.opensubtitles.org/subtitles/%s' % id)
        except BrowserHTTPNotFound:
            return
        if self.is_on_page(SubtitlePage):
            return self.page.get_subtitle()
