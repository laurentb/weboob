# -*- coding: utf-8 -*-

# Copyright(C) 2018 Julien Veyssier
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
import re

from weboob.tools.misc import get_bytes_size
from weboob.capabilities.torrent import Torrent
from weboob.capabilities.base import NotLoaded, NotAvailable

from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.pages import HTMLPage, LoggedPage, RawPage, pagination
from weboob.browser.filters.standard import Regexp, CleanText, CleanDecimal, Format
from weboob.browser.filters.html import CleanHTML, AbsoluteLink


class SearchPage(LoggedPage, HTMLPage):
    @pagination
    @method
    class iter_torrents(ListElement):
        next_page = AbsoluteLink('//a[@rel="next"]')
        item_xpath = '//table[has-class("table")]/tbody/tr'

        class item(ItemElement):
            klass = Torrent
            obj_id = CleanText('.//a[@id="get_nfo"]/@target')
            obj_name = CleanText('.//td[2]//text()')
            obj_seeders = CleanDecimal('./td[last()-1]/text()', default=0)
            obj_leechers = CleanDecimal('./td[last()]/text()', default=0)
            obj_description = NotLoaded
            obj_files = NotLoaded
            obj_filename = Format('%s.torrent', obj_name)
            obj_magnet = NotAvailable
            def obj_url(self):
                return '%sengine/download_torrent?id=%s' % (self.page.browser.BASEURL, self.obj_id)

            def obj_size(self):
                rawsize = CleanText('./td[last()-3]')(self)
                nsize = float(re.sub(r'[A-Za-z]', '', rawsize))
                usize = re.sub(r'[.0-9]', '', rawsize).strip().replace('o', 'B').upper()
                size = get_bytes_size(nsize, usize)
                return size


class TorrentPage(LoggedPage, HTMLPage):

    @method
    class get_torrent(ItemElement):
        klass = Torrent
        obj_description = CleanHTML('//div[has-class("description-header")]/following-sibling::div[1]')
        obj_name = CleanText('//div[@id="title"]')
        obj_id = Regexp(CleanText('//a[has-class("butt")]/@href'), '/download_torrent\?id=([0-9]+)', '\\1')
        obj_url = CleanText('//a[has-class("butt")]/@href')
        obj_filename = obj_name
        def obj_size(self):
            rawsize = CleanText('//table[has-class("informations")]//td[text()="Taille totale"]/following-sibling::td')(self)
            nsize = float(re.sub(r'[A-Za-z]', '', rawsize))
            usize = re.sub(r'[.0-9]', '', rawsize).strip().replace('o', 'B').upper()
            size = get_bytes_size(nsize, usize)
            return size
        obj_files = NotAvailable
        obj_seeders = CleanDecimal('//table[has-class("infos-torrent")]//tr[@id="adv_search_cat"]/td[text()="Seeders"]/following-sibling::td[1]', default=0)
        obj_leechers = CleanDecimal('//table[has-class("infos-torrent")]//tr[@id="adv_search_cat"]/td[text()="Leechers"]/following-sibling::td[1]', default=0)
        obj_magnet = NotAvailable


class DownloadPage(LoggedPage, RawPage):
    pass
