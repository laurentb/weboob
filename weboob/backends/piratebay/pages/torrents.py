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

        for table in self.document.getiterator('table'):
            if table.attrib.get('id','') != 'searchResult':
                raise Exception('You''re in serious troubles!')
            else:
                for tr in table.getiterator('tr'):
                    if tr.get('class','') != "header":
                        td = tr.getchildren()[1]
                        div = td.getchildren()[0]
                        link = div.find('a').attrib['href']
                        title = div.find('a').text
                        idt = link.split('/')[2]

                        a = td.getchildren()[1]
                        url = a.attrib['href']

                        size = td.find('font').text.split(',')[1]
                        size = size.split(' ')[2]
                        u = size[-3:].replace('i','')
                        size = size[:-3]

                        seed = tr.getchildren()[2].text
                        leech = tr.getchildren()[3].text

                        torrent = Torrent(idt,
                                          title,
                                          url=url,
                                          size=self.unit(float(size),u),
                                          seeders=int(seed),
                                          leechers=int(leech))
                        yield torrent

class TorrentPage(BasePage):
    def get_torrent(self, id):
        for div in self.document.getiterator('div'):
            if div.attrib.get('id','') == 'title':
                title = div.text
            elif div.attrib.get('class','') == 'download':
                url = div.getchildren()[0].attrib.get('href','')
            elif div.attrib.get('id','') == 'details':
                size = float(div.getchildren()[0].getchildren()[5].text.split('(')[1].split('Bytes')[0])
                seed = div.getchildren()[1].getchildren()[7].text
                leech = div.getchildren()[1].getchildren()[9].text
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
