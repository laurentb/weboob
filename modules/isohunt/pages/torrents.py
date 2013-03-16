# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Julien Veyssier
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


from weboob.capabilities.torrent import Torrent
from weboob.tools.browser import BasePage
from weboob.tools.misc import get_bytes_size
from weboob.capabilities.base import NotAvailable, NotLoaded


__all__ = ['TorrentsPage']


class TorrentsPage(BasePage):
    def iter_torrents(self):
        for tr in self.document.getiterator('tr'):
            if tr.attrib.get('class', '') == 'hlRow':
                # sometimes the first tr also has the attribute hlRow
                # i use that to ditinct it from the others
                if 'onmouseout' in tr.attrib:
                    size = NotAvailable
                    seed = NotAvailable
                    leech = NotAvailable
                    atitle = tr.getchildren()[2].getchildren()[1]
                    title = unicode(atitle.text)
                    if not title:
                        title = u''
                    for bold in atitle.getchildren():
                        if bold.text:
                            title += bold.text
                        if bold.tail:
                            title += bold.tail
                    idt = tr.getchildren()[2].getchildren()[0].attrib.get('href', '')
                    idt = idt.split('/')[2]
                    size = tr.getchildren()[3].text
                    u = size[-2:]
                    size = float(size[:-3])
                    sseed = tr.getchildren()[4].text
                    sleech = tr.getchildren()[5].text
                    if sseed is not None and sseed != "":
                        seed = int(sseed)
                    if sleech is not None and sleech != "":
                        leech = int(sleech)
                    url = u'https://isohunt.com/download/%s/mon_joli_torrent.torrent' % idt
                    torrent = Torrent(idt, title)
                    torrent.url = url
                    torrent.size = get_bytes_size(size, u)
                    torrent.seeders = seed
                    torrent.leechers = leech
                    torrent.description = NotLoaded
                    torrent.files = NotLoaded
                    yield torrent


class TorrentPage(BasePage):
    def get_torrent(self, id):
        title = NotAvailable
        size = NotAvailable
        url = 'https://isohunt.com/download/%s/%s.torrent' % (id, id)
        title = unicode(self.parser.select(
            self.document.getroot(), 'head > meta[name=title]', 1).attrib.get('content', ''))
        seed = NotAvailable
        leech = NotAvailable
        tip_id = "none"
        for span in self.document.getiterator('span'):
            if span.attrib.get('style', '') == 'color:green;' and ('ShowTip' in span.attrib.get('onmouseover', '')):
                seed = int(span.tail.split(' ')[1])
                tip_id = span.attrib.get('onmouseover', '').split("'")[1]
        for div in self.document.getiterator('div'):
            # find the corresponding super tip which appears on super mouse hover!
            if div.attrib.get('class', '') == 'dirs ydsf' and tip_id in div.attrib.get('id', ''):
                leech = int(div.getchildren()[0].getchildren()[1].tail.split(' ')[2])
            # the <b> with the size in it doesn't have a distinction
            # have to get it by higher
            elif div.attrib.get('id', '') == 'torrent_details':
                size = div.getchildren()[6].getchildren()[0].getchildren()[0].text
                u = size[-2:]
                size = float(size[:-3])
                size = get_bytes_size(size, u)

        # files and description (uploader's comment)
        description = NotAvailable
        files = []
        count_p_found = 0
        for p in self.document.getiterator('p'):
            if p.attrib.get('style', '') == 'line-height:1.2em;margin-top:1.8em':
                count_p_found += 1
                if count_p_found == 1:
                    if p.getchildren()[1].tail is not None:
                        description = unicode(p.getchildren()[1].tail)
                if count_p_found == 2:
                    if p.getchildren()[0].text == 'Directory:':
                        files.append(p.getchildren()[0].tail.strip() + '/')
                    else:
                        files.append(p.getchildren()[0].tail.strip())

        for td in self.document.getiterator('td'):
            if td.attrib.get('class', '') == 'fileRows':
                filename = td.text
                for slash in td.getchildren():
                    filename += '/'
                    filename += slash.tail
                files.append(filename)

        torrent = Torrent(id, title)
        torrent.url = url
        torrent.size = size
        torrent.seeders = seed
        torrent.leechers = leech
        torrent.description = description
        torrent.files = files
        return torrent
