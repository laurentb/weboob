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

from .pages import SearchPage, SubtitlePage, LANGUAGE_NUMBERS


__all__ = ['PodnapisiBrowser']


class PodnapisiBrowser(Browser):
    DOMAIN = 'www.podnapisi.net'
    PROTOCOL = 'http'
    ENCODING = 'utf-8'
    USER_AGENT = Browser.USER_AGENTS['wget']
    PAGES = {
        'http://www.podnapisi.net/fr/ppodnapisi/search\?sJ=[0-9]*&sK=.*&sS=downloads&sO=desc': SearchPage,
        'http://www.podnapisi.net/fr/ppodnapisi/podnapis/i/[0-9]*': SubtitlePage
    }

    def iter_subtitles(self, language, pattern):
        nlang = LANGUAGE_NUMBERS[language]
        self.location('http://www.podnapisi.net/fr/ppodnapisi/search?sJ=%s&sK=%s&sS=downloads&sO=desc' % (nlang, pattern.encode('utf-8')))
        assert self.is_on_page(SearchPage)
        return self.page.iter_subtitles(unicode(language))

    def get_subtitle(self, id):
        try:
            self.location('http://www.podnapisi.net/fr/ppodnapisi/podnapis/i/%s' % id)
        except BrowserHTTPNotFound:
            return
        if self.is_on_page(SubtitlePage):
            return self.page.get_subtitle(id)
