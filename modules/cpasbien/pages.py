# -*- coding: utf-8 -*-

# Copyright(C) 2016 Julien Veyssier
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
from weboob.browser.filters.standard import Regexp, CleanText, Type, Format
from weboob.browser.filters.html import CleanHTML


class SearchPage(HTMLPage):

    @method
    class iter_torrents(ListElement):
        item_xpath = '//div[has-class("ligne0") or has-class("ligne1")]'

        class item(ItemElement):
            klass = Torrent
            obj_id = Regexp(CleanText('.//a[has-class("titre")]/@href'),
                    '.*dl-torrent/(.*).html')
            obj_name = CleanText('.//a[has-class("titre")]', default=NotAvailable)
            obj_magnet = NotAvailable
            obj_seeders = CleanText('.//div[has-class("up")]', default=NotAvailable) & Type(type=int)
            obj_leechers = CleanText('.//div[has-class("down")]', default=NotAvailable) & Type(type=int)

            obj_description = NotLoaded
            obj_files = NotLoaded

            def obj_url(self):
                href = CleanText('.//a[has-class("titre")]/@href')(self)
                subid = href.split('/')[-1].replace('.html','.torrent')
                return 'http://www.cpasbien.cm/telechargement/%s'%subid

            def obj_size(self):
                rawsize = CleanText('./div[has-class("poid")]')(self)
                rawsize = rawsize.replace(',','.').strip()
                nsize = float(rawsize.split()[0])
                usize = rawsize.split()[-1].upper().replace('O','B')
                size = get_bytes_size(nsize,usize)
                return size

            obj_filename = Format('%s.torrent', Regexp(
                             CleanText('.//a[has-class("titre")]/@href'),
                             '/([^/]*)\.html')
                           )


class TorrentPage(HTMLPage):
    @method
    class get_torrent(ItemElement):
        klass = Torrent

        obj_name = CleanText('//h2[has-class("h2fiche")]', default=NotAvailable)
        obj_description = CleanHTML('//div[@id="textefiche"]', default=NotAvailable)
        obj_seeders = CleanText('//div[@id="infosficher"]//span[has-class("seed_ok")]') & Type(type=int)
        obj_leechers = CleanText('(//div[@id="infosficher"]/span)[3]') & Type(type=int)
        obj_magnet = NotAvailable

        obj_id = Regexp(CleanText('//h2[has-class("h2fiche")]/a/@href'),
                        '.*dl-torrent/(.*).html')
        obj_url = Format('http://www.cpasbien.cm%s', CleanText('//a[@id="telecharger"]/@href'))

        def obj_size(self):
            rawsize = CleanText('(//div[@id="infosficher"]/span)[1]')(self)
            rawsize = rawsize.replace(',','.').strip()
            nsize = float(rawsize.split()[0])
            usize = rawsize.split()[-1].upper().replace('O','B')
            size = get_bytes_size(nsize,usize)
            return size

        obj_files = NotAvailable

        obj_filename = CleanText(Regexp(CleanText('//a[@id="telecharger"]/@href'),
                        '.*telechargement/(.*)'), default=NotAvailable)

