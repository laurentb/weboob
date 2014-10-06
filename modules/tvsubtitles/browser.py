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

from .pages import SeriePage, SearchPage, SeasonPage, HomePage


__all__ = ['TvsubtitlesBrowser']

LANGUAGE_LIST = ['en', 'es', 'fr', 'de', 'br', 'ru', 'ua', 'it', 'gr',
                 'ar', 'hu', 'pl', 'tr', 'nl', 'pt', 'sv', 'da', 'fi',
                 'ko', 'cn', 'jp', 'bg', 'cz', 'ro']


class TvsubtitlesBrowser(Browser):
    DOMAIN = 'www.tvsubtitles.net'
    PROTOCOL = 'http'
    ENCODING = 'utf-8'
    USER_AGENT = Browser.USER_AGENTS['wget']
    PAGES = {
        'http://www.tvsubtitles.net': HomePage,
        'http://www.tvsubtitles.net/search.php': SearchPage,
        'http://www.tvsubtitles.net/tvshow-.*.html': SeriePage,
        'http://www.tvsubtitles.net/subtitle-[0-9]*-[0-9]*-.*.html': SeasonPage
    }

    def iter_subtitles(self, language, pattern):
        self.location('http://www.tvsubtitles.net')
        assert self.is_on_page(HomePage)
        return self.page.iter_subtitles(language, pattern)

    def get_subtitle(self, id):
        try:
            self.location('http://www.tvsubtitles.net/subtitle-%s.html' % id)
        except BrowserHTTPNotFound:
            return
        if self.is_on_page(SeasonPage):
            return self.page.get_subtitle()
