# -*- coding: utf-8 -*-

# Copyright(C) 2010  Julien Veyssier
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


from weboob.capabilities.torrent import Torrent
from weboob.tools.browser import BasePage
from weboob.tools.misc import get_bytes_size


__all__ = ['TorrentsPage']


class TorrentsPage(BasePage):
    def iter_torrents(self):
        for tr in self.document.getiterator('tr'):
            if tr.attrib.get('class', '') == 'odd' or tr.attrib.get('class', '') == ' even':
                title = tr.getchildren()[0].getchildren()[1].getchildren()[1].text
                if not title:
                    title = ''
                for red in tr.getchildren()[0].getchildren()[1].getchildren()[1].getchildren():
                    if red.text:
                        title += red.text
                    if red.tail:
                        title += red.tail
                idt = tr.getchildren()[0].getchildren()[1].getchildren()[1].attrib.get('href', '').replace('/', '') \
                    .replace('.html', '')

                # look for url
                child = tr.getchildren()[0]
                while child.attrib.get('href', None) is None and len(child.getchildren()) > 0:
                    child = child.getchildren()[0]
                url = child.get('href', '')

                size = tr.getchildren()[1].text
                u = tr.getchildren()[1].getchildren()[0].text
                size = size = size.replace(',', '.')
                size = float(size)
                seed = tr.getchildren()[4].text
                leech = tr.getchildren()[5].text

                yield Torrent(idt,
                              title,
                              url=url,
                              size=get_bytes_size(size, u),
                              seeders=int(seed),
                              leechers=int(leech))


class TorrentPage(BasePage):
    def get_torrent(self, id):
        seed = 0
        leech = 0
        description = 'No description'
        url = 'No Url found'
        for div in self.document.getiterator('div'):
            if div.attrib.get('id', '') == 'desc':
                description = div.text.strip()
                for ch in div.getchildren():
                    if ch.tail != None:
                        description += ' '+ch.tail.strip()
            if div.attrib.get('class', '') == 'seedBlock':
                seed = int(div.getchildren()[1].text)
            if div.attrib.get('class', '') == 'leechBlock':
                leech = int(div.getchildren()[1].text)

        for h in self.document.getiterator('h1'):
            if h.attrib.get('class', '') == 'torrentName':
                title = h.getchildren()[0].getchildren()[0].text

        for a in self.document.getiterator('a'):
            if ('Download' in a.attrib.get('title', '')) and ('torrent file' in a.attrib.get('title', '')):
                url = a.attrib.get('href', '')

        size = 0
        for span in self.document.getiterator('span'):
            if span.attrib.get('class', '') == 'folder' or span.attrib.get('class', '') == 'folderopen':
                size = span.getchildren()[1].tail
                u = span.getchildren()[2].text
                size = float(size.split(': ')[1].replace(',', '.'))

        files = []
        for td in self.document.getiterator('td'):
            if td.attrib.get('class', '') == 'torFileName':
                files.append(td.text)

        torrent = Torrent(id, title)
        torrent = Torrent(id, title)
        torrent.url = url
        torrent.size = get_bytes_size(size, u)
        torrent.seeders = int(seed)
        torrent.leechers = int(leech)
        torrent.description = description
        torrent.files = files
        return torrent
