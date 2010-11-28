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
            if tr.attrib.get('class','') == 'hlRow':
                # TODO à corriger
                atitle = tr.getchildren()[2].getchildren()[1]
                title = atitle.text
                if not title:
                    title = ''
                for bold in atitle.getchildren():
                    if bold.text:
                        title += bold.text
                    if bold.tail:
                        title += bold.tail
                idt = tr.getchildren()[2].getchildren()[0].attrib.get('href','')
                idt = idt.split('/')[2]
                size = tr.getchildren()[3].text
                u = size[-2:]
                size = float(size[:-3])
                seed = tr.getchildren()[4].text
                leech = tr.getchildren()[5].text
                url = 'https://isohunt.com/download/%s/mon_joli_torrent.torrent' % idt

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
        title = ''
        description = 'No description'
        url = 'https://isohunt.com/download/%s/%s.torrent' % (id , id)
        for a in self.document.getiterator('a'):
            if 'Search more torrents of' in a.attrib.get('title',''):
                title = a.tail
        for span in self.document.getiterator('span'):
            if span.attrib.get('style','') == 'color:green;' and ('ShowTip' in span.attrib.get('onmouseover','')):
                seed = span.tail.split(' ')[1]
                break
        leech = 0

        files = []
        count_p_found = 0
        for p in self.document.getiterator('p'):
            if p.attrib.get('style','') == "line-height:1.2em;margin-top:1.8em":
                count_p_found += 1
                if count_p_found == 1:
                    description = p.getchildren()[1].tail
                if count_p_found == 2:
                    if p.getchildren()[0].text == 'Directory:':
                        files.append(p.getchildren()[0].tail.strip()+'/')
                    else:
                        files.append(p.getchildren()[0].tail.strip())

        # TODO marche pas
        for td in self.document.getiterator('td'):
            print td.attrib.get('class')
            if td.attrib.get('class','') == 'fileRows':
                #files.append(td.text)
                filename = td.text
                print "len"+str(len(td.getchildren()))
                for slash in td.getchildren():
                    filename += '/'
                    filename += slash.tail
                files.append(filename)


                
        # TODO leechers


        size = 0
        u = 'MB'
                
        #--------------------------TODO

        torrent = Torrent(id, title)
        torrent.url = url
        torrent.size = self.unit(size,u)
        torrent.seeders = int(seed)
        torrent.leechers = int(leech)
        torrent.description = description
        torrent.files = files
                    
        return torrent
