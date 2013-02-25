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

from .pages import SeriePage, SearchPage, SeasonPage,HomePage


__all__ = ['OpensubtitlesBrowser']

LANGUAGE_CONV = {
'ar':'ara', 'eo':'epo',  'ga':'',    'ru':'rus',
'af':''   , 'et':'est',  'it':'ita', 'sr':'scc',
'sq':'alb', 'tl':''   ,  'ja':'jpn', 'sk':'slo',
'hy':'arm', 'fi':'fin',  'kn':'',    'sl':'slv',
'az':''   , 'fr':'fre',  'ko':'kor', 'es':'spa',
'eu':'baq', 'gl':'glg',  'la':'',    'sw':'swa',
'be':''   , 'ka':'geo',  'lv':'lav', 'sv':'swe',
'bn':'ben', 'de':'ger',  'lt':'lit', 'ta':'',
'bg':'bul', 'gr':'ell',  'mk':'mac', 'te':'tel',
'ca':'cat', 'gu':''   ,  'ms':'may', 'th':'tha',
'zh':'chi', 'ht':''   ,  'mt':'',    'tr':'tur',
'hr':'hrv', 'iw':'heb',  'no':'nor', 'uk':'ukr',
'cz':'cze', 'hi':'hin',  'fa':'per', 'ur':'urd',
'da':'dan', 'hu':'hun',  'pl':'pol', 'vi':'vie',
'nl':'dut', 'is':'ice',  'pt':'por', 'cy':'',
'en':'eng', 'id':'ind',  'ro':'rum', 'yi':''}

class TvsubtitlesBrowser(BaseBrowser):
    DOMAIN = 'www.tvsubtitles.net'
    PROTOCOL = 'http'
    ENCODING = 'utf-8'
    USER_AGENT = BaseBrowser.USER_AGENTS['wget']
    PAGES = {
        'http://www.tvsubtitles.net': HomePage,
        'http://www.tvsubtitles.net/search.php': SearchPage,
        'http://www.tvsubtitles.net/tvshow-.*.html': SeriePage,
        'http://www.tvsubtitles.net/subtitle-[0-9]*-[0-9]*-.*.html' : SeasonPage
        }

    def iter_subtitles(self, language, pattern):
        self.location('http://www.tvsubtitles.net')
        assert self.is_on_page(HomePage)
        return self.page.iter_subtitles(language,pattern)

    def get_subtitle(self, id):
        self.location('http://www.tvsubtitles.net/subtitle-%s.html' % id)
        assert self.is_on_page(SeasonPage)
        return self.page.get_subtitle()
