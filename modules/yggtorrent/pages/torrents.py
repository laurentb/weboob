# -*- coding: utf-8 -*-

# Copyright(C) 2018 Julien Veyssier
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
from weboob.browser.pages import HTMLPage, LoggedPage, RawPage
from weboob.browser.filters.standard import Regexp, CleanText, CleanDecimal, Type, Format
from weboob.browser.filters.html import CleanHTML


class SearchPage(LoggedPage, HTMLPage):

    @method
    class iter_torrents(ListElement):
        item_xpath = '//table[contains(@class,"table")]/tbody/tr'

        class item(ItemElement):
            klass = Torrent
            obj_id = CleanText('.//a[@id="get_nfo"]/@target')
            obj_name = CleanText('.//a[@class="torrent-name"]/text()')
            obj_seeders = CleanDecimal('./td[last()-1]/text()', default=0)
            obj_leechers = CleanDecimal('./td[last()]/text()', default=0)
            obj_description = NotLoaded
            obj_files = NotLoaded
            obj_filename = Format('%s.torrent', obj_name)
            obj_magnet = NotAvailable
            obj_url = CleanText('.//a/@href[contains(.,"download_torrent")]')

            def obj_size(self):
                rawsize = CleanText('./td[last()-2]')(self)
                nsize = float(re.sub(r'[A-Za-z]', '', rawsize))
                usize = re.sub(r'[.0-9]', '', rawsize).upper()
                size = get_bytes_size(nsize, usize)
                return size


class TorrentPage(LoggedPage, HTMLPage):

    @method
    class get_torrent(ItemElement):
        klass = Torrent
        obj_description = CleanHTML('//div[@id="description"]')
        obj_name = CleanText('/html/head/title/text()')
        obj_id = Regexp(CleanText('//a/@href[contains(.,"download_torrent")]'), '/download_torrent\?id=([0-9]+)', '\\1')
        obj_url = CleanText('//a/@href[contains(.,"download_torrent")]')
        obj_filename = CleanText('//input[@id="torrent_id"]/../div[has-class("panel-title")]/b', default=NotAvailable)
        def obj_size(self):
            rawsize = CleanText('//tr[@id="vpn_link"]/../tr[7]/td[2]')(self)
            nsize = float(re.sub(r'[A-Za-z]', '', rawsize))
            usize = re.sub(r'[.0-9]', '', rawsize).upper()
            size = get_bytes_size(nsize, usize)
            return size
        obj_files = NotAvailable
        obj_seeders = CleanDecimal('//span[has-class("seed")]/text()', default=0)
        obj_leechers = CleanDecimal('//span[has-class("leech")]/text()', default=0)
        obj_magnet = NotAvailable


class DownloadPage(LoggedPage, RawPage):
    pass
