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



from weboob.tools.browser import BasePage
from weboob.capabilities.torrent import Torrent


__all__ = ['TorrentsPage']


class TorrentsPage(BasePage):
    def unit(self, n, u):
        m = {'KB': 1024,
             'MB': 1024*1024,
             'GB': 1024*1024*1024,
             'TB': 1024*1024*1024*1024,
            }
        return float(n*m[u])

    def iter_torrents(self):

        for tr in self.document.getiterator('tr'):
            if tr.attrib.get('class','') == 'odd' or tr.attrib.get('class','') == ' even':
                title = tr.getchildren()[0].getchildren()[1].getchildren()[1].text
                if not title:
                    title = ''
                for red in tr.getchildren()[0].getchildren()[1].getchildren()[1].getchildren():
                    if red.text:
                        title += red.text
                    if red.tail:
                        title += red.tail
                idt = tr.getchildren()[0].getchildren()[1].getchildren()[1].attrib.get('href','').replace('/','').replace('.html','')
                url = tr.getchildren()[0].getchildren()[0].getchildren()[0].getchildren()[0].attrib.get('href','')
                size = tr.getchildren()[1].text
                u = tr.getchildren()[1].getchildren()[0].text
                size = size = size.replace(',','.')
                size = float(size)
                seed = tr.getchildren()[4].text
                leech = tr.getchildren()[5].text

                torrent = Torrent(idt,
                                  title,
                                  url=url,
                                  size=self.unit(size,u),
                                  seeders=int(seed),
                                  leechers=int(leech))
                yield torrent

class TorrentPage(BasePage):
    def unit(self, n, u):
        m = {'KB': 1024,
             'MB': 1024*1024,
             'GB': 1024*1024*1024,
             'TB': 1024*1024*1024*1024,
            }
        return float(n*m[u])

    def get_torrent(self, id):

        description = "No description"
        for div in self.document.getiterator('div'):
            if div.attrib.get('id','') == 'desc':
                description = div.text.strip()
        for td in self.document.getiterator('td'):
            if td.attrib.get('class','') == 'hreview-aggregate':
                seed = int(td.getchildren()[2].getchildren()[0].getchildren()[0].text)
                leech = int(td.getchildren()[2].getchildren()[1].getchildren()[0].text)
                url = td.getchildren()[3].getchildren()[0].attrib.get('href')
                title = td.getchildren()[1].getchildren()[0].getchildren()[0].text

        size = 0
        for span in self.document.getiterator('span'):
            if span.attrib.get('class','') == "folder" or span.attrib.get('class','') == "folderopen":
                size = span.getchildren()[1].tail
                u = size.split(' ')[-1].split(')')[0]
                size = float(size.split(': ')[1].split(' ')[0].replace(',','.'))

        files = []
        for td in self.document.getiterator('td'):
            if td.attrib.get('class','') == 'torFileName':
                files.append(td.text)


        torrent = Torrent(id, title)
        torrent = Torrent(id, title)
        torrent.url = url
        torrent.size = self.unit(size,u)
        torrent.seeders = int(seed)
        torrent.leechers = int(leech)
        torrent.description = description
        torrent.files = files
                    
        return torrent
