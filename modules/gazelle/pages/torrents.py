# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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
from logging import warning, debug

from weboob.tools.compat import parse_qs, urlparse
from weboob.tools.misc import get_bytes_size
from weboob.tools.html import html2text
from weboob.capabilities.torrent import Torrent
from weboob.capabilities.base import NotLoaded

from .base import BasePage


class TorrentsPage(BasePage):
    TORRENTID_REGEXP = re.compile('torrents\.php\?action=download&id=(\d+)')

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
                    elif len(tds) in (8, 9):
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
                        title = ' - '.join([a.text for a in tds[i].findall('a')])
                    url = urlparse(tds[i].find('a').attrib['href'])
                    params = parse_qs(url.query)
                    if 'torrentid' in params:
                        id = '%s.%s' % (params['id'][0], params['torrentid'][0])
                    else:
                        url = tds[i].find('span').find('a').attrib['href']
                        m = self.TORRENTID_REGEXP.match(url)
                        if not m:
                            continue
                        id = '%s.%s' % (params['id'][0], m.group(1))
                    try:
                        size, unit = tds[i + 3].text.split()
                    except ValueError:
                        size, unit = tds[i + 2].text.split()
                    size = get_bytes_size(float(size.replace(',', '')), unit)
                    seeders = int(tds[-2].text)
                    leechers = int(tds[-1].text)

                    torrent = Torrent(id, title)
                    torrent.url = self.format_url(url)
                    torrent.size = size
                    torrent.seeders = seeders
                    torrent.leechers = leechers
                    yield torrent
                else:
                    debug('unknown attrib: %s' % tr.attrib)

    def get_torrent(self, id):
        table = self.browser.parser.select(self.document.getroot(), 'div.thin', 1)

        h2 = table.xpath('.//h2')
        if len(h2) > 0:
            title = u''.join([txt.strip() for txt in h2[0].itertext()])
        else:
            title = self.browser.parser.select(table, 'div.title_text', 1).text

        torrent = Torrent(id, title)
        if '.' in id:
            torrentid = id.split('.', 1)[1]
        else:
            torrentid = id
        table = self.browser.parser.select(self.document.getroot(), 'table.torrent_table')
        if len(table) == 0:
            table = self.browser.parser.select(self.document.getroot(), 'div.main_column', 1)
            is_table = False
        else:
            table = table[0]
            is_table = True

        for tr in table.findall('tr' if is_table else 'div'):
            if is_table and 'group_torrent' in tr.attrib.get('class', ''):
                tds = tr.findall('td')

                if not len(tds) == 5:
                    continue

                url = tds[0].find('span').find('a').attrib['href']
                m = self.TORRENTID_REGEXP.match(url)
                if not m:
                    warning('ID not found')
                    continue
                if m.group(1) != torrentid:
                    continue

                torrent.url = self.format_url(url)
                size, unit = tds[1].text.split()
                torrent.size = get_bytes_size(float(size.replace(',', '')), unit)
                torrent.seeders = int(tds[3].text)
                torrent.leechers = int(tds[4].text)
                break
            elif not is_table and tr.attrib.get('class', '').startswith('torrent_widget') \
                    and tr.attrib.get('class', '').endswith('pad'):
                url = tr.cssselect('a[title=Download]')[0].attrib['href']
                m = self.TORRENTID_REGEXP.match(url)
                if not m:
                    warning('ID not found')
                    continue
                if m.group(1) != torrentid:
                    continue

                torrent.url = self.format_url(url)
                size, unit = tr.cssselect('div.details_title strong')[-1].text.strip('()').split()
                torrent.size = get_bytes_size(float(size.replace(',', '')), unit)
                torrent.seeders = int(tr.cssselect('img[title=Seeders]')[0].tail)
                torrent.leechers = int(tr.cssselect('img[title=Leechers]')[0].tail)
                break

        if not torrent.url:
            warning('Torrent %s not found in list' % torrentid)
            return None

        div = self.parser.select(self.document.getroot(), 'div.main_column', 1)
        for box in div.cssselect('div.box'):
            title = None
            body = None

            title_t = box.cssselect('div.head')
            if len(title_t) > 0:
                title_t = title_t[0]
                if title_t.find('strong') is not None:
                    title_t = title_t.find('strong')
                if title_t.text is not None:
                    title = title_t.text.strip()

            body_t = box.cssselect('div.body,div.desc')
            if body_t:
                body = html2text(self.parser.tostring(body_t[-1])).strip()

            if title and body:
                if torrent.description is NotLoaded:
                    torrent.description = u''
                torrent.description += u'%s\n\n%s\n' % (title, body)

        divs = self.document.getroot().cssselect('div#files_%s,div#filelist_%s,tr#torrent_%s td' % (torrentid, torrentid, torrentid))
        if divs:
            torrent.files = []
            for div in divs:
                table = div.find('table')
                if table is None:
                    continue
                for tr in table:
                    if tr.attrib.get('class', None) != 'colhead_dark':
                        torrent.files.append(tr.find('td').text)

        return torrent
