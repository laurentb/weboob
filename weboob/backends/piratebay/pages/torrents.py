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


import re
from logging import warning, debug

from weboob.tools.misc import html2text
from weboob.tools.browser import BasePage
from weboob.capabilities.torrent import Torrent
from weboob.capabilities.base import NotLoaded


__all__ = ['TorrentsPage']


class TorrentsPage(BasePage):
    #TORRENTID_REGEXP = re.compile('torrents\.php\?action=download&id=(\d+)')
    def unit(self, n, u):
        m = {'KB': 1024,
             'MB': 1024*1024,
             'GB': 1024*1024*1024,
             'TB': 1024*1024*1024*1024,
            }
        return float(n.replace(',', '')) * m.get(u, 1)

    #def format_url(self, url):
    #    return '%s://%s/%s' % (self.browser.PROTOCOL,
    #                           self.browser.DOMAIN,
    #                           url)

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
                        print "u:"+u
                        size = size[:-3]
                        print 'size:'+size
                        
                        seed = tr.getchildren()[2].text
                        leech = tr.getchildren()[3].text

                        torrent = Torrent(idt,
                                          title,
                                          url=url,
                                          size=self.unit(size.replace('.',','),u),
                                          seeders=int(seed),
                                          leechers=int(leech))
                        yield torrent

    def get_torrent(self, id):
        table = self.document.getroot().cssselect('div.thin')
        if not table:
            warning('No div.thin found')
            return None

        h2 = table[0].find('h2')
        title = h2.text or ''
        if h2.find('a') != None:
            title += h2.find('a').text + h2.find('a').tail

        torrent = Torrent(id, title)
        table = self.document.getroot().cssselect('table.torrent_table')
        if not table:
            warning('No table found')
            return None

        for tr in table[0].findall('tr'):
            if tr.attrib.get('class', '').startswith('group_torrent'):
                tds = tr.findall('td')

                if not len(tds) == 5:
                    continue

                url = tds[0].find('span').find('a').attrib['href']
                id = self.TORRENTID_REGEXP.match(url)

                if not id:
                    warning('ID not found')
                    continue

                id = id.group(1)

                if id != torrent.id:
                    continue

                torrent.url = self.format_url(url)
                torrent.size = self.unit(*tds[1].text.split())
                torrent.seeders = int(tds[3].text)
                torrent.leechers = int(tds[4].text)
                break

        if not torrent.url:
            warning('Torrent %d not found in list' % torrent.id)
            return None

        div = self.document.getroot().cssselect('div.main_column')
        if not div:
            warning('WTF')
            return None

        for box in div[0].cssselect('div.box'):
            title = None
            body = None

            title_t = box.cssselect('div.head')
            if title_t:
                title = title_t[0].find('strong').text.strip()
            body_t = box.cssselect('div.body')
            if body_t:
                body = html2text(self.browser.parser.tostring(body_t[0])).strip()

            if title and body:
                if torrent.description is NotLoaded:
                    torrent.description = u''
                torrent.description += u'%s\n\n%s\n' % (title, body)

        div = self.document.getroot().cssselect('div#files_%s' % torrent.id)
        if div:
            torrent.files = []
            for tr in div[0].find('table'):
                if tr.attrib.get('class', None) != 'colhead_dark':
                    torrent.files.append(tr.find('td').text)

        return torrent
