# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Julien Veyssier, Laurent Bachelier
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


from urlparse import parse_qs, urlsplit

from weboob.capabilities.torrent import Torrent
from weboob.capabilities.base import NotAvailable, NotLoaded
from weboob.tools.browser import BasePage
from weboob.tools.misc import get_bytes_size


__all__ = ['TorrentsPage', 'TorrentPage']


class TorrentsPage(BasePage):
    def iter_torrents(self):
        for tr in self.document.getiterator('tr'):
            if tr.attrib.get('class', '') == 'odd' or tr.attrib.get('class', '') == ' even':
                magnet = NotAvailable
                url = NotAvailable
                if not 'id' in tr.attrib:
                    continue
                title = tr.find('.//a[@class="cellMainLink"]')
                if title is None:
                    title = u''
                else:
                    title = unicode(title.text)
                for red in tr.getchildren()[0].getchildren()[1].getchildren()[1].getchildren():
                    title += red.text_content()
                idt = tr.getchildren()[0].getchildren()[1].getchildren()[1].attrib.get('href', '').replace('/', '') \
                    .replace('.html', '')

                # look for url
                for a in self.parser.select(tr, 'div.iaconbox a'):
                    href = a.attrib.get('href', '')
                    if href.startswith('magnet'):
                        magnet = unicode(href)
                    elif href.startswith('http'):
                        url = unicode(href)
                    elif href.startswith('//'):
                        url = u'https:%s' % href

                size = tr.getchildren()[1].text
                u = tr.getchildren()[1].getchildren()[0].text
                size = size = size.replace(',', '.')
                size = float(size)
                seed = tr.getchildren()[4].text
                leech = tr.getchildren()[5].text

                torrent = Torrent(idt, title)
                torrent.url = url
                torrent.magnet = magnet
                torrent.description = NotLoaded
                torrent.files = NotLoaded
                torrent.filename = unicode(parse_qs(urlsplit(url).query).get('title', [None])[0])
                torrent.size = get_bytes_size(size, u)
                torrent.seeders = int(seed)
                torrent.leechers = int(leech)
                yield torrent


class TorrentPage(BasePage):
    def get_torrent(self, id):
        seed = 0
        leech = 0
        description = NotAvailable
        url = NotAvailable
        magnet = NotAvailable
        title = NotAvailable
        for div in self.document.getiterator('div'):
            if div.attrib.get('id', '') == 'desc':
                try:
                    description = unicode(div.text_content().strip())
                except UnicodeDecodeError:
                    description = 'Description with invalid UTF-8.'
            elif div.attrib.get('class', '') == 'seedBlock':
                if div.getchildren()[1].text is not None:
                    seed = int(div.getchildren()[1].text)
                else:
                    seed = 0
            elif div.attrib.get('class', '') == 'leechBlock':
                if div.getchildren()[1].text is not None:
                    leech = int(div.getchildren()[1].text)
                else:
                    leech = 0

        title = self.parser.select(self.document.getroot(),
                                   'h1.novertmarg span', 1)
        title = unicode(title.text)

        for a in self.parser.select(self.document.getroot(),
                                    'div.downloadButtonGroup a'):
            href = a.attrib.get('href', '')
            if href.startswith('magnet'):
                magnet = unicode(href)
            elif href.startswith('//'):
                url = u'https:%s' % href
            elif href.startswith('http'):
                url = unicode(href)

        size = 0
        u = ''
        for span in self.document.getiterator('span'):
            # sometimes there are others span, this is not so sure but the size of the children list
            # is enough to know if this is the right span
            if (span.attrib.get('class', '') == 'folder'
                or span.attrib.get('class', '') == 'folderopen') \
                    and len(span.getchildren()) > 2:
                size = span.getchildren()[1].tail
                u = span.getchildren()[2].text
                size = float(size.split(': ')[1].replace(',', '.'))

        files = []
        for td in self.document.getiterator('td'):
            if td.attrib.get('class', '') == 'torFileName':
                files.append(td.text)

        torrent = Torrent(id, title)
        torrent.url = url
        if torrent.url:
            torrent.filename = parse_qs(urlsplit(url).query).get('title', [None])[0]
        torrent.magnet = magnet
        torrent.size = get_bytes_size(size, u)
        torrent.seeders = int(seed)
        torrent.leechers = int(leech)
        if description == '':
            description = NotAvailable
        torrent.description = description
        torrent.files = files
        return torrent
