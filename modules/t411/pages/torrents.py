# -*- coding: utf-8 -*-

# Copyright(C) 2015-2016 Julien Veyssier
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


import re

from weboob.tools.misc import get_bytes_size
from weboob.capabilities.torrent import Torrent
from weboob.capabilities.base import NotLoaded, NotAvailable

from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.filters.standard import Regexp, CleanText, Type, Format
from weboob.browser.filters.html import CleanHTML


class SearchPage(LoggedPage, HTMLPage):

    @method
    class iter_torrents(ListElement):
        item_xpath = '//table[@class="results"]/tbody/tr'

        class item(ItemElement):
            klass = Torrent
            obj_id = Regexp(CleanText('./td[3]/a/@href'),
                            '/torrents/nfo/\?id=(.*)')
            obj_name = CleanText('./td[2]/a/@title')
            obj_seeders = CleanText('./td[8]') & Type(type=int)
            obj_leechers = CleanText('./td[9]') & Type(type=int)
            obj_description = NotLoaded
            obj_files = NotLoaded
            obj_filename = Format('%s.torrent',CleanText('./td[2]/a/@title'))
            obj_magnet = NotAvailable

            def obj_url(self):
                fullid = Regexp(CleanText('./td[3]/a/@href'),'/torrents/nfo/\?id=(.*)')(self)
                downurl = 'https://www.t411.in/torrents/download/?id=%s'%fullid
                return downurl

            def obj_size(self):
                rawsize = CleanText('./td[6]')(self)
                nsize = float(rawsize.split()[0])
                usize = rawsize.split()[-1].upper()
                size = get_bytes_size(nsize,usize)
                return size


class TorrentPage(LoggedPage, HTMLPage):
    @method
    class get_torrent(ItemElement):
        klass = Torrent

        def obj_description(self):
            desctxt = CleanHTML('//div[has-class("description")]/article')(self)
            strippedlines = '\n'.join([s.strip() for s in desctxt.split('\n') if re.search(r'\[[0-9]+\]', s) is None])
            description = re.sub(r'\s\s+', '\n\n', strippedlines)
            return description

        obj_name = CleanText('//div[has-class("torrentDetails")]/h2/span/text()')

        obj_id = CleanText('//input[@id="torrent-id"][1]/@value')

        def obj_url(self):
            fullid = CleanText('//input[@id="torrent-id"][1]/@value')(self)
            downurl = 'https://www.t411.in/torrents/download/?id=%s'%fullid
            return downurl

        obj_filename = CleanText('//div[@class="accordion"]//tr[th="Torrent"]/td')
        def obj_size(self):
            rawsize = CleanText('//div[@class="accordion"]//tr[th="Taille totale"]/td')(self)
            nsize = float(rawsize.split()[0])
            usize = rawsize.split()[-1].upper()
            size = get_bytes_size(nsize,usize)
            return size

        def obj_files(self):
            res = []
            for f in Type('//div[@class="accordion"]/h3[text()="Liste des Fichiers"]\
                          /following-sibling::div[1]//tr', type=list)(self)[1:]:
                res.append(CleanText(f)(self))
            return res

        obj_seeders = CleanText('//div[@class="details"]//td[@class="up"]') & Type(type=int)
        obj_leechers = CleanText('//div[@class="details"]//td[@class="down"]') & Type(type=int)
        obj_magnet = NotAvailable
