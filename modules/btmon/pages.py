# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Julien Veyssier
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


import string

from weboob.capabilities.torrent import Torrent
from weboob.capabilities.base import NotAvailable
from weboob.tools.browser import BasePage
from weboob.tools.misc import get_bytes_size


__all__ = ['TorrentsPage','TorrentPage']


class TorrentsPage(BasePage):
    def iter_torrents(self):
        for div in self.parser.select(self.document.getroot(),'div.list_tor'):
            a = self.parser.select(div,'a.list_tor_title',1)
            href = a.attrib.get('href','')
            self.browser.location('http://%s%s'%(self.browser.DOMAIN,href))
            assert self.browser.is_on_page(TorrentPage)
            yield self.browser.page.get_torrent()


class TorrentPage(BasePage):
    def get_torrent(self):
        seed = 0
        leech = 0
        description = NotAvailable.__unicode__()
        url = NotAvailable
        magnet = NotAvailable
        title = NotAvailable
        id = self.browser.geturl().split('.html')[0].split('/')[-1]

        div = self.parser.select(self.document.getroot(),'div#middle_content',1)
        title = u'%s'%self.parser.select(self.document.getroot(),'div#middle_content > h1',1).text
        slblock_values = self.parser.select(div,'div.sl_block b')
        if len(slblock_values) >= 2:
            seed = slblock_values[0].text
            leech = slblock_values[1].text
        href_t = self.parser.select(div,'a.down',1).attrib.get('href','')
        url = 'http://%s%s'%(self.browser.DOMAIN,href_t)
        magnet = self.parser.select(div,'a.magnet',1).attrib.get('href','')
        
        divtabs = self.parser.select(div,'div#tabs',1)
        files_div = self.parser.select(divtabs,'div.body > div.doubleblock > div.leftblock')
        files = []
        if len(files_div) > 0:
            size_text = self.parser.select(files_div,'h5',1).text
            for b in self.parser.select(files_div,'b'):
                div = b.getparent()
                files.append(div.text_content())
        else:
            size_text = self.parser.select(divtabs,'h5',1).text_content()
        size_text = size_text.split('(')[1].split(')')[0].strip()
        size = float(size_text.split(',')[1].strip(string.letters))
        u = size_text.split(',')[1].strip().translate(None,string.digits).strip('.').strip().upper()
        div_desc = self.parser.select(divtabs,'div#descriptionContent')
        if len(div_desc) > 0:
            description = div_desc[0].text_content()

        torrent = Torrent(id, title)
        torrent.url = url
        torrent.filename = id
        torrent.magnet = magnet
        torrent.size = get_bytes_size(size, u)
        torrent.seeders = int(seed)
        torrent.leechers = int(leech)
        torrent.description = description
        torrent.files = files
        return torrent
