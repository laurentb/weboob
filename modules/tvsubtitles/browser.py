# -*- coding: utf-8 -*-

# Copyright(C) 2013 Julien Veyssier
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from weboob.browser import PagesBrowser, URL
from weboob.browser.exceptions import BrowserHTTPNotFound

from .pages import SeriePage, SearchPage, SeasonPage, HomePage


__all__ = ['TvsubtitlesBrowser']

LANGUAGE_LIST = ['en', 'es', 'fr', 'de', 'br', 'ru', 'ua', 'it', 'gr',
                 'ar', 'hu', 'pl', 'tr', 'nl', 'pt', 'sv', 'da', 'fi',
                 'ko', 'cn', 'jp', 'bg', 'cz', 'ro']


class TvsubtitlesBrowser(PagesBrowser):
    BASEURL = 'http://www.tvsubtitles.net'

    search = URL(r'/search.php', SearchPage)
    serie = URL(r'/tvshow-.*.html', SeriePage)
    season = URL(r'/subtitle-(?P<id>[0-9]*-[0-9]*-.*).html', SeasonPage)
    home = URL(r'/', HomePage)

    def iter_subtitles(self, language, pattern):
        self.home.go()
        assert self.home.is_here()
        return self.page.iter_subtitles(language, pattern)

    def get_subtitle(self, id):
        try:
            self.season.go(id=id)
        except BrowserHTTPNotFound:
            return
        if self.season.is_here():
            return self.page.get_subtitle()
