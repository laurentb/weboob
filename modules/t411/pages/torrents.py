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

from weboob.browser.pages import HTMLPage, FormNotFound, LoggedPage
from weboob.browser.filters.standard import Regexp, CleanText, Format, Env, Type
from weboob.browser.filters.html import CleanHTML


class SearchPage(LoggedPage, HTMLPage):

    def iter_torrents(self):
        for tr in self.doc.getroot().cssselect('table.results tbody tr'):
            tds = tr.findall('td')
            tdlink = tds[1]
            tlink = tdlink.findall('a')[0]
            title = tlink.attrib.get('title','')
            nfolink = tds[2].cssselect('a.nfo')[0]
            fullid = nfolink.attrib.get('href','').split('=')[-1]

            downurl = 'https://www.t411.in/torrents/download/?id=%s'%fullid

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

            torrent = Torrent(fullid, title)
            torrent.url = downurl
            torrent.size = size
            torrent.seeders = seeders
            torrent.leechers = leechers
            torrent.magnet = NotAvailable
            torrent.description = NotLoaded
            torrent.files = NotLoaded
            torrent.filename = NotLoaded
            yield torrent


class TorrentPage(LoggedPage, HTMLPage):
    def get_torrent(self, id):
        seeders = 0
        leechers = 0
        description = NotAvailable
        title = NotAvailable
        filename = NotAvailable
        files = []
        size = 0

        divdesc = self.doc.getroot().cssselect('div.description')[0]
        #print(dir(self.doc.parser))

        # TODO clean that dirty field
        description = divdesc.text_content()
        #print(dir(divdesc))
        #desctxt = html2text(divdesc.get('content'))

        #divdesc = self.browser.parser.select(self.document.getroot(), 'div.description', 1)
        #strippedlines = '\n'.join([s.strip() for s in desctxt.split('\n') if re.search(r'\[[0-9]+\]', s) is None])
        #description = re.sub(r'\s\s+', '\n\n', strippedlines)

        title = self.doc.getroot().cssselect('div.torrentDetails h2 span')[0].text

        fullid = self.doc.getroot().cssselect('input[id=torrent-id]')[0].attrib.get('value')
        downurl = 'https://www.t411.in/torrents/download/?id=%s'%fullid

        accor_lines = self.doc.getroot().cssselect('div.accordion tr')
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

        h3titles = self.doc.getroot().cssselect('div.accordion h3.title')
        for h3 in h3titles:
            if h3.text == 'Liste des Fichiers':
                divfiles = h3.getnext()
                dlines = divfiles.cssselect('tr')
                for l in dlines[1:]:
                    files.append(re.sub('\s+', ' ', l.text_content().strip()))

        seedtxt = self.doc.getroot().cssselect('div.details td.up')[0].text_content()
        seeders = int(seedtxt)

        leecherstxt = self.doc.getroot().cssselect('div.details td.down')[0].text_content()
        leechers = int(leecherstxt)


        torrent = Torrent(fullid, title)
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
