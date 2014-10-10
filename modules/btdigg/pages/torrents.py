# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from urlparse import urlparse, parse_qs

from weboob.tools.misc import get_bytes_size
from weboob.deprecated.browser import Page,BrokenPageError
from weboob.capabilities.torrent import Torrent, MagnetOnly
from weboob.capabilities.base import NotAvailable


class TorrentsPage(Page):

    def iter_torrents(self):
        try:
            table = self.document.getroot().cssselect('table.torrent_name_tbl')
        except BrokenPageError:
            return
        for i in range(0, len(table), 2):
            # Title
            title = table[i].cssselect('td.torrent_name a')[0]
            name = unicode(title.text)
            url = unicode(title.attrib['href'])

            # Other elems
            elems = table[i+1].cssselect('td')

            magnet = unicode(elems[0].cssselect('a')[0].attrib['href'])

            query = urlparse(magnet).query # xt=urn:btih:<...>&dn=<...>
            btih = parse_qs(query)['xt'][0] # urn:btih:<...>
            ih = btih.split(':')[-1]

            value, unit = elems[2].cssselect('span.attr_val')[0].text.split()

            valueago, valueunit, _ = elems[5].cssselect('span.attr_val')[0].text.split()
            delta = timedelta(**{valueunit: float(valueago)})
            date = datetime.now() - delta

            url = unicode('https://btdigg.org/search?info_hash=%s' % ih)

            torrent = Torrent(ih, name)
            torrent.url = url
            torrent.size = get_bytes_size(float(value), unit)
            torrent.magnet = magnet
            torrent.seeders = NotAvailable
            torrent.leechers = NotAvailable
            torrent.description = NotAvailable
            torrent.files = NotAvailable
            torrent.date = date
            yield torrent


class TorrentPage(Page):
    def get_torrent(self, id):
        trs = self.document.getroot().cssselect('table.torrent_info_tbl tr')

        # magnet
        download = trs[2].cssselect('td a')[0]
        if download.attrib['href'].startswith('magnet:'):
            magnet = unicode(download.attrib['href'])

            query = urlparse(magnet).query # xt=urn:btih:<...>&dn=<...>
            btih = parse_qs(query)['xt'][0] # urn:btih:<...>
            ih = btih.split(':')[-1]

        name = unicode(trs[3].cssselect('td')[1].text)

        value, unit  = trs[5].cssselect('td')[1].text.split()

        valueago, valueunit, _ = trs[6].cssselect('td')[1].text.split()
        delta = timedelta(**{valueunit: float(valueago)})
        date = datetime.now() - delta

        files = []
        for tr in trs[15:]:
            files.append(unicode(tr.cssselect('td')[1].text))

        torrent = Torrent(ih, name)
        torrent.url = unicode(self.url)
        torrent.size = get_bytes_size(float(value), unit)
        torrent.magnet = magnet
        torrent.seeders = NotAvailable
        torrent.leechers = NotAvailable
        torrent.description = NotAvailable
        torrent.files = files
        torrent.filename = NotAvailable
        torrent.date = date

        return torrent

    def get_torrent_file(self, id):
        raise MagnetOnly(self.get_torrent(id).magnet)
