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

from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.pages import HTMLPage, pagination
from weboob.browser.filters.standard import Regexp, CleanText, CleanDecimal, Format
from weboob.browser.filters.html import AbsoluteLink


class SearchPage(HTMLPage):
    @pagination
    @method
    class iter_torrents(ListElement):
        next_page = AbsoluteLink('//a[@id="next"]')
        item_xpath = '//table[has-class("table2")]//tr[position()>1]'

        class item(ItemElement):
            klass = Torrent
            def obj_url(self):
                url = Regexp(AbsoluteLink('.//div[has-class("tt-name")]/a[1]'), '(^.*)\?.*', '\\1')(self)
                return url.replace('http://', 'https://')
            obj_id = Regexp(CleanText('.//div[has-class("tt-name")]/a[2]/@href'), '/.*-torrent-([0-9]+)\.html$', '\\1')
            obj_name = CleanText('.//div[has-class("tt-name")]/a[2]/text()')
            obj_seeders = CleanDecimal('.//td[has-class("tdseed")]', default=0)
            obj_leechers = CleanDecimal('.//td[has-class("tdleech")]', default=0)
            obj_filename = Format('%s.torrent', obj_name)

            def obj_size(self):
                rawsize = CleanText('(.//td[has-class("tdnormal")])[2]')(self)
                nsize = float(re.sub(r'[A-Za-z]', '', rawsize))
                usize = re.sub(r'[.0-9 ]', '', rawsize).upper()
                size = get_bytes_size(nsize, usize)
                return size


class TorrentPage(HTMLPage):
    @method
    class get_torrent(ItemElement):
        klass = Torrent
        obj_name = CleanText('.//div[@id="content"]/h1')
        obj_id = Regexp(CleanText('//div[@id="updatestatslink"]/a/@onclick'), 'torrent_id=([0-9]+)&', '\\1')
        def obj_url(self):
            url = Regexp(AbsoluteLink('//div[has-class("torrentinfo")]//div[has-class("dltorrent")]//a[text()="Download torrent"]'), '(^.*)\?.*', '\\1')(self)
            return url.replace('http://', 'https://')
        obj_filename = Format('%s.torrent', obj_name)
        def obj_size(self):
            s = CleanText('//td/b[text()="Size"]/../../td[2]')(self)
            nsize = float(re.sub(r'[A-Za-z]', '', s))
            usize = re.sub(r'[.0-9 ]', '', s).upper()
            size = get_bytes_size(nsize, usize)
            return size
        def obj_files(self):
            res = []
            for f in self.xpath('//div[has-class("fileline")]'):
                res.append(CleanText(f)(self))
            return res
        obj_seeders = CleanDecimal('//div[@id="content"]/span[has-class("greenish")]', default=0)
        obj_leechers = CleanDecimal('//div[@id="content"]/span[has-class("reddish")]', default=0)
        obj_magnet = AbsoluteLink('//div[has-class("torrentinfo")]//div[has-class("dltorrent")]//a[text()="Magnet Link"]')

