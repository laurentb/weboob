# -*- coding: utf-8 -*-

# Copyright(C) 2010-2016 Julien Veyssier, Laurent Bachelier
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


from weboob.capabilities.torrent import Torrent
from weboob.capabilities.base import NotLoaded, NotAvailable
from weboob.tools.misc import get_bytes_size

from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.pages import HTMLPage
from weboob.browser.filters.standard import Regexp, CleanText, Type


class SearchPage(HTMLPage):

    @method
    class iter_torrents(ListElement):
        item_xpath = '//table[has-class("data")]//tr[@class="odd" or @class="even"]'

        class item(ItemElement):
            klass = Torrent
            obj_id = Regexp(CleanText('.//div[@class="torrentname"]//a[@class="cellMainLink"]/@href'),
                    '.*-t([0-9]*).html')
            obj_name = CleanText('.//a[@class="cellMainLink"]', default=NotAvailable)
            obj_magnet = CleanText('.//div[has-class("iaconbox")]//a[starts-with(@href,"magnet")]/@href', default=NotAvailable)
            obj_seeders = CleanText('.//td[has-class("green") and has-class("center")]', default=NotAvailable) & Type(type=int)
            obj_leechers = CleanText('.//td[has-class("red") and has-class("center")]', default=NotAvailable) & Type(type=int)

            obj_description = NotLoaded
            obj_files = NotLoaded

            def obj_url(self):
                href = CleanText('.//div[has-class("iaconbox")]//a[starts-with(@href,"//")]/@href')(self)
                return 'https:%s'%href

            def obj_size(self):
                rawsize = CleanText('./td[2]')(self)
                rawsize = rawsize.replace(',','.')
                nsize = float(rawsize.split()[0])
                usize = rawsize.split()[-1].upper()
                size = get_bytes_size(nsize,usize)
                return size

            obj_filename = CleanText(Regexp(CleanText('.//div[has-class("iaconbox")]//a[starts-with(@href,"//")]/@href'),
                    '.*title=(.*)'), default=NotAvailable)



class TorrentPage(HTMLPage):
    @method
    class get_torrent(ItemElement):
        klass = Torrent

        obj_description = CleanText('//div[@id="desc"]', default=NotAvailable)
        obj_seeders = CleanText('(//div[has-class("seedBlock")]/strong)[1]') & Type(type=int)
        obj_leechers = CleanText('(//div[has-class("leechBlock")]/strong)[1]') & Type(type=int)
        obj_name = CleanText('//h1[has-class("novertmarg")]//span', default=NotAvailable)
        obj_magnet = CleanText('//div[has-class("downloadButtonGroup")]//a[starts-with(@href,"magnet")]/@href', default=NotAvailable)

        obj_id = Regexp(CleanText('//h1[has-class("novertmarg")]/a/@href'),
                        '.*-t([0-9]*)\.html')
        def obj_url(self):
            href = CleanText('//div[has-class("downloadButtonGroup")]//a[starts-with(@href,"//")]/@href')(self)
            return u'https:%s'%href

        def obj_size(self):
            rawsize = CleanText('//span[has-class("folder") or has-class("folderopen")]')(self)
            rawsize = rawsize.split(': ')[-1].split(')')[0].strip()
            rawsize = rawsize.replace(',','.')
            nsize = float(rawsize.split()[0])
            usize = rawsize.split()[-1].upper()
            size = get_bytes_size(nsize,usize)
            return size

        def obj_files(self):
            res = []
            for f in Type('//td[has-class("torFileName")]', type=list)(self):
                res.append(CleanText(f)(self))
            return res

        obj_filename = CleanText(Regexp(CleanText('//div[has-class("downloadButtonGroup")]//a[starts-with(@href,"//")]/@href'),
                        '.*title=(.*)'), default=NotAvailable)

