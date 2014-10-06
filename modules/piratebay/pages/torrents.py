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


from weboob.deprecated.browser import Page,BrokenPageError
from weboob.capabilities.torrent import Torrent
from weboob.capabilities.base import NotAvailable, NotLoaded

from html2text import unescape


class TorrentsPage(Page):
    def unit(self, n, u):
        m = {'B': 1,
                'KB': 1024,
                'MB': 1024 * 1024,
                'GB': 1024 * 1024 * 1024,
                'TB': 1024 * 1024 * 1024 * 1024,
                }
        return float(n * m[u])

    def iter_torrents(self):
        try:
            table = self.parser.select(self.document.getroot(), 'table#searchResult', 1)
        except BrokenPageError:
            return
        first = True
        for tr in table.getiterator('tr'):
            if first:
                first = False
                continue
            if tr.get('class', '') != "header":
                td = tr.getchildren()[1]
                div = td.getchildren()[0]
                link = div.find('a').attrib['href']
                title = unicode(unescape(div.find('a').text))
                idt = link.split('/')[2]

                a = td.getchildren()[1]
                url = unicode(a.attrib['href'])

                size = td.find('font').text.split(',')[1].strip()
                u = size.split(' ')[1].split(u'\xa0')[1].replace('i', '')
                size = size.split(' ')[1].split(u'\xa0')[0]

                seed = tr.getchildren()[2].text
                leech = tr.getchildren()[3].text

                torrent = Torrent(idt, title)
                torrent.url = url
                torrent.size = self.unit(float(size), u)
                torrent.seeders = int(seed)
                torrent.leechers = int(leech)
                torrent.description = NotLoaded
                torrent.files = NotLoaded
                torrent.magnet = NotLoaded
                yield torrent


class TorrentPage(Page):
    def get_torrent(self, id):
        url = NotAvailable
        magnet = NotAvailable
        for div in self.document.getiterator('div'):
            if div.attrib.get('id', '') == 'title':
                title = unicode(unescape(div.text.strip()))
            elif div.attrib.get('class', '') == 'download':
                for link in self.parser.select(div, 'a'):
                    href = link.attrib.get('href', '')
                    # https fails on the download server, so strip it
                    if href.startswith('https://'):
                        href = href.replace('https://', 'http://', 1)
                    if href.startswith('magnet:'):
                        magnet = unicode(href)
                    elif len(href):
                        url = unicode(href)
            elif div.attrib.get('id', '') == 'details':
                size = float(div.getchildren()[0].getchildren()[5].text.split('(')[1].split('Bytes')[0])
                if len(div.getchildren()) > 1 \
                and div.getchildren()[1].attrib.get('class', '') == 'col2':
                    child_to_explore = div.getchildren()[1]
                else:
                    child_to_explore = div.getchildren()[0]
                prev_child_txt = "none"
                seed = "-1"
                leech = "-1"
                for ch in child_to_explore.getchildren():
                    if prev_child_txt == "Seeders:":
                        seed = ch.text
                    if prev_child_txt == "Leechers:":
                        leech = ch.text
                    prev_child_txt = ch.text
            elif div.attrib.get('class', '') == 'nfo':
                description = unicode(div.getchildren()[0].text_content().strip())
        torrent = Torrent(id, title)
        torrent.url = url or NotAvailable
        torrent.magnet = magnet
        torrent.size = size
        torrent.seeders = int(seed)
        torrent.leechers = int(leech)
        torrent.description = description
        torrent.files = NotAvailable

        return torrent
