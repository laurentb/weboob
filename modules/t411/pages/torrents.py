# -*- coding: utf-8 -*-

# Copyright(C) 2015-2016 Julien Veyssier
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

from weboob.tools.misc import get_bytes_size
from weboob.capabilities.torrent import Torrent
from weboob.capabilities.base import NotLoaded, NotAvailable

from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.pages import HTMLPage, LoggedPage, RawPage
from weboob.browser.filters.standard import Regexp, CleanText, Type, Format
from weboob.browser.filters.html import CleanHTML


class SearchPage(LoggedPage, HTMLPage):

    @method
    class iter_torrents(ListElement):
        item_xpath = '//table[@class="category-list"]/tbody/tr[@class="bordergrey isItem isItemDesk"]'

        class item(ItemElement):
            klass = Torrent
            obj_id = Regexp(CleanText('./td[2]/a/@href'), '/torrents/([0-9]+)/(\w+)', '\\1')
            obj_name = Regexp(CleanText('./td[2]/a/@href'), '/torrents/([0-9]+)/([-\w]+)', '\\2')
            obj_seeders = CleanText('./td[6]/span[text()]') & Type(type=int)
            obj_leechers = CleanText('./td[7]/span[text()]') & Type(type=int)
            obj_description = NotLoaded
            obj_files = NotLoaded
            obj_filename = Format('%s.torrent', obj_name)
            obj_magnet = NotAvailable
            obj_url = CleanText('./td[2]/a/@href')

            def obj_size(self):
                rawsize = CleanText('./td[5]')(self)
                nsize = float(rawsize.split()[0])
                usize = rawsize.split()[-1].upper()
                size = get_bytes_size(nsize, usize)
                return size


class TorrentPage(LoggedPage, HTMLPage):

    @method
    class get_torrent(ItemElement):
        klass = Torrent
        obj_description = CleanHTML('/html/body/div[2]/div/div[2]/div[1]/p/span[3]/span')
        obj_name = CleanText('//title1[has-class("noh ww")]/text()')
        obj_id = CleanText('//input[@id="torrent-id"][1]/@value')
        obj_url = CleanText('//tr/td/a/@href[contains(.,"telecharger")]')
        obj_filename = NotAvailable
        obj_size = NotAvailable
        obj_files = NotAvailable
        obj_seeders = NotAvailable
        obj_leechers = NotAvailable
        obj_magnet = NotAvailable


class DownloadPage(LoggedPage, RawPage):
    pass
