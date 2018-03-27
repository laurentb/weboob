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
from weboob.capabilities.base import NotAvailable

from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.pages import HTMLPage, pagination
from weboob.browser.filters.standard import Regexp, CleanText, CleanDecimal, Format
from weboob.browser.filters.html import AbsoluteLink


class SearchPage(HTMLPage):
    @pagination
    @method
    class iter_torrents(ListElement):
        next_page = AbsoluteLink('//div[has-class("pagination")]/a[last()]')
        item_xpath = '//div[has-class("list_tor")]'

        class item(ItemElement):
            klass = Torrent
            obj_id = Regexp(CleanText('.//a[has-class("list_tor_title")]/@href'), '/(.*)\.torrent\.html$', '\\1')
            obj_name = CleanText('.//a[has-class("list_tor_title")]')
            obj_seeders = CleanDecimal('.//b[has-class("green")]/text()', default=0)
            obj_leechers = CleanDecimal('.//b[has-class("red")]/text()', default=0)
            obj_filename = Format('%s.torrent', obj_name)
            obj_url = AbsoluteLink('.//a[@title="Download torrent"]')

            def obj_size(self):
                rawsize = Regexp(CleanText('.//div[has-class("list_tor_right")]/p[1]/span[1]'), 'Size: (.*)$', '\\1')(self)
                nsize = float(re.sub(r'[A-Za-z]', '', rawsize))
                usize = re.sub(r'[.0-9 ]', '', rawsize).upper()
                size = get_bytes_size(nsize, usize)
                return size


class TorrentPage(HTMLPage):
    @method
    class get_torrent(ItemElement):
        klass = Torrent
        obj_name = CleanText('.//div[@id="middle_content"]/h1')
        obj_description = CleanText('//div[@id="descriptionContent"]', default=NotAvailable)
        obj_id = Regexp(CleanText('//div[@id="middle_content"]/a[@title="Download torrent"]/@href'), '/(.*)\.torrent', '\\1')
        obj_url = AbsoluteLink('//div[@id="middle_content"]/a[@title="Download torrent"]')
        obj_filename = Format('%s.torrent', obj_name)
        def obj_size(self):
            rawsize = CleanText('//div[has-class("files")]/../h5')(self)
            s = rawsize.split(',')[-1].replace(')', '')
            nsize = float(re.sub(r'[A-Za-z]', '', s))
            usize = re.sub(r'[.0-9 ]', '', s).upper()
            size = get_bytes_size(nsize, usize)
            return size
        def obj_files(self):
            res = []
            for f in self.xpath('//div[has-class("files")]//div[not(has-class("wrapper"))]'):
                res.append(CleanText(f)(self))
            return res
        obj_seeders = CleanDecimal('//div[has-class("sl_block")]/b[1]', default=0)
        obj_leechers = CleanDecimal('//div[has-class("sl_block")]/b[2]', default=0)
        obj_magnet = CleanText('.//a[has-class("magnet")]/@href')

class HomePage(HTMLPage):
    pass
