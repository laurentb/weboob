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
        #return float(n.replace(',', '')) * m.get(u, 1)
        return float(n*m[u])

    def iter_torrents(self):

        for tr in self.document.getiterator('tr'):
            if tr.attrib.get('class','') == 'odd' or tr.attrib.get('class','') == ' even':
                title = tr.getchildren()[0].getchildren()[1].getchildren()[1].text
                idt = tr.getchildren()[0].getchildren()[1].getchildren()[1].attrib.get('href','').replace('/','').replace('.html','')
                url = tr.getchildren()[0].getchildren()[0].getchildren()[0].getchildren()[0].attrib.get('href','')
                size = tr.getchildren()[1].text
                u = size[-2:]
                size = size = size[:-3].replace(',','.')
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
    def get_torrent(self, id):
        for div in self.document.getiterator('div'):
            if div.attrib.get('id','') == 'title':
                title = div.text.strip()
            elif div.attrib.get('class','') == 'download':
                url = div.getchildren()[0].attrib.get('href','')
            elif div.attrib.get('id','') == 'details':
                size = float(div.getchildren()[0].getchildren()[5].text.split('(')[1].split('Bytes')[0])
                if len(div.getchildren()) > 1 \
                        and div.getchildren()[1].attrib.get('class','') == 'col2' :
                    seed = div.getchildren()[1].getchildren()[7].text
                    leech = div.getchildren()[1].getchildren()[9].text
                else:
                    seed = div.getchildren()[0].getchildren()[24].text
                    leech = div.getchildren()[0].getchildren()[26].text
            elif div.attrib.get('class','') == 'nfo':
                description = div.getchildren()[0].text
        torrent = Torrent(id, title)
        torrent.url = url
        torrent.size = size
        torrent.seeders = int(seed)
        torrent.leechers = int(leech)
        torrent.description = description
        torrent.files = ['NYI']

        return torrent
