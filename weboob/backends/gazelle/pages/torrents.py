# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
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
    TORRENTID_REGEXP = re.compile('torrents\.php\?action=download&id=(\d+)')
    def unit(self, n, u):
        m = {'KB': 1024,
             'MB': 1024*1024,
             'GB': 1024*1024*1024,
             'TB': 1024*1024*1024*1024,
            }
        return float(n.replace(',', '')) * m.get(u, 1)

    def format_url(self, url):
        return '%s://%s/%s' % (self.browser.PROTOCOL,
                               self.browser.DOMAIN,
                               url)

    def iter_torrents(self):
        table = self.document.getroot().cssselect('table.torrent_table')
        if not table:
            table = self.document.getroot().cssselect('table#browse_torrent_table')
        if table:
            table = table[0]
            current_group = None
            for tr in table.findall('tr'):
                if tr.attrib.get('class', '') == 'colhead':
                    # ignore
                    continue
                if tr.attrib.get('class', '') == 'group':
                    tds = tr.findall('td')
                    current_group = u''
                    div = tds[-6]
                    if div.getchildren()[0].tag == 'div':
                        div = div.getchildren()[0]
                    for a in div.findall('a'):
                        if not a.text:
                            continue
                        if current_group:
                            current_group += ' - '
                        current_group += a.text
                elif tr.attrib.get('class', '').startswith('group_torrent') or \
                     tr.attrib.get('class', '').startswith('torrent'):
                    tds = tr.findall('td')

                    title = current_group
                    if len(tds) == 7:
                        # Under a group
                        i = 0
                    elif len(tds) in (8,9):
                        # An alone torrent
                        i = len(tds) - 1
                        while i >= 0 and tds[i].find('a') is None:
                            i -= 1
                    else:
                        # Useless title
                        continue

                    if title:
                        title += u' (%s)' % tds[i].find('a').text
                    else:
                        title = tds[i].find('a').text
                    url = tds[i].find('span').find('a').attrib['href']
                    id = self.TORRENTID_REGEXP.match(url)
                    if not id:
                        continue
                    id = id.group(1)
                    size = self.unit(*tds[i+3].text.split())
                    seeders = int(tds[-2].text)
                    leechers = int(tds[-1].text)

                    torrent = Torrent(id,
                                      title,
                                      url=self.format_url(url),
                                      size=size,
                                      seeders=seeders,
                                      leechers=leechers)
                    yield torrent
                else:
                    debug('unknown attrib: %s' % tr.attrib)

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
