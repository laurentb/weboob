# -*- coding: utf-8 -*-

# Copyright(C) 2015 Julien Veyssier
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
from weboob.tools.html import html2text
from weboob.capabilities.torrent import Torrent
from weboob.capabilities.base import NotLoaded, NotAvailable

from .base import BasePage


class SearchPage(BasePage):

    def format_url(self, url):
        return '%s://%s/%s' % (self.browser.PROTOCOL,
                               self.browser.DOMAIN,
                               url)

    def iter_torrents(self):
        #table = self.document.getroot().cssselect('table.results', 1)
        trs = self.parser.select(self.document.getroot(), 'table.results tbody tr')
        if len(trs) > 0:
            for tr in trs:
                tds = tr.findall('td')
                tdlink = tds[1]
                tlink = tdlink.findall('a')[0]
                title = tlink.attrib.get('title','')
                nfolink = self.parser.select(tds[2], 'a.nfo')[0]
                id = nfolink.attrib.get('href','').split('=')[-1]

                downurl = 'https://www.t411.in/torrents/download/?id=%s'%id
                #detailurl = 'https://www.t411.in/t/%s'%id

                rawsize = tds[5].text
                nsize = float(rawsize.split()[0])
                usize = rawsize.split()[-1].upper()
                size = get_bytes_size(nsize,usize)
                try:
                    seeders = int(tds[7].text)
                except ValueError:
                    seeders = 0
                try:
                    leechers = int(tds[8].text)
                except ValueError:
                    leechers = 0

                torrent = Torrent(id, title)
                torrent.url = self.format_url(downurl)
                torrent.size = size
                torrent.seeders = seeders
                torrent.leechers = leechers
                torrent.magnet = NotAvailable
                torrent.description = NotLoaded
                torrent.files = NotLoaded
                torrent.filename = NotLoaded
                yield torrent


class TorrentPage(BasePage):
    def get_torrent(self, id):
        seeders = 0
        leechers = 0
        description = NotAvailable
        title = NotAvailable
        filename = NotAvailable
        files = []
        size = 0

        divdesc = self.browser.parser.select(self.document.getroot(), 'div.description', 1)
        desctxt = html2text(self.parser.tostring(divdesc))
        strippedlines = '\n'.join([s.strip() for s in desctxt.split('\n') if re.search(r'\[[0-9]+\]', s) is None])
        description = re.sub(r'\s\s+', '\n\n', strippedlines)

        title = self.browser.parser.select(self.document.getroot(), 'div.torrentDetails h2 span', 1).text

        downurl = 'https://www.t411.in/torrents/download/?id=%s'%id

        accor_lines = self.parser.select(self.document.getroot(), 'div.accordion tr')
        if len(accor_lines) > 0:
            for tr in accor_lines:
                th = tr.findall('th')
                td = tr.findall('td')
                if len(th)>0 and len(td):
                    if th[0].text == 'Taille totale':
                        rawsize = td[0].text
                        nsize = float(rawsize.split()[0])
                        usize = rawsize.split()[-1].upper()
                        size = get_bytes_size(nsize,usize)
                    elif th[0].text == 'Torrent':
                        filename = td[0].text_content().strip()

        h3titles = self.parser.select(self.document.getroot(), 'div.accordion h3.title')
        for h3 in h3titles:
            if h3.text == 'Liste des Fichiers':
                divfiles = h3.getnext()
                dlines = self.parser.select(divfiles, 'tr')
                for l in dlines[1:]:
                    files.append(re.sub('\s+', ' ', l.text_content().strip()))

        seedtxt = self.browser.parser.select(self.document.getroot(), 'div.details td.up', 1).text_content()
        seeders = int(seedtxt)

        leecherstxt = self.browser.parser.select(self.document.getroot(), 'div.details td.down', 1).text_content()
        leechers = int(leecherstxt)


        torrent = Torrent(id, title)
        torrent.name = title
        torrent.url = downurl
        torrent.magnet = NotAvailable
        torrent.size = size
        torrent.description = description
        torrent.seeders = seeders
        torrent.leechers = leechers
        torrent.files = files
        torrent.filename = filename
        return torrent
