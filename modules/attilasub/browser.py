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

from .pages import SubtitlesPage, SearchPage


__all__ = ['AttilasubBrowser']


class AttilasubBrowser(Browser):
    DOMAIN = 'davidbillemont3.free.fr'
    PROTOCOL = 'http'
    ENCODING = 'windows-1252'
    USER_AGENT = Browser.USER_AGENTS['wget']
    PAGES = {
        'http://search.freefind.com/find.html.*': SearchPage,
        'http://davidbillemont3.free.fr/.*.htm': SubtitlesPage,
    }

    def iter_subtitles(self, language, pattern):
        self.location('http://search.freefind.com/find.html?id=81131980&_charset_=&bcd=%%F7&scs=1&pageid=r&query=%s&mode=Find%%20pages%%20matching%%20ALL%%20words' %
                      pattern.encode('utf-8'))
        assert self.is_on_page(SearchPage)
        return self.page.iter_subtitles(language, pattern)

    def get_subtitle(self, id):
        url_end = id.split('|')[0]
        try:
            self.location('http://davidbillemont3.free.fr/%s' % url_end)
        except BrowserHTTPNotFound:
            return
        if self.is_on_page(SubtitlesPage):
            return self.page.get_subtitle(id)
