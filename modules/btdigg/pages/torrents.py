# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from weboob.tools.misc import get_bytes_size
from weboob.browser.pages import HTMLPage
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.capabilities.torrent import Torrent, MagnetOnly
from weboob.browser.filters.standard import CleanText, Regexp


class TorrentsPage(HTMLPage):
    @method
    class iter_torrents(ListElement):
        item_xpath = '//div[@id="search_res"]/table/tr'

        class item(ItemElement):
            klass = Torrent

            obj_id = Regexp(CleanText('./td/table/tr/td[@class="torrent_name"]/a/@href'),
                            r'info_hash=([0-9a-f]+)', '\\1')
            obj_name = CleanText('./td/table/tr/td[@class="torrent_name"]')
            obj_magnet = CleanText('./td/table/tr/td[@class="ttth"]/a/@href')

            def obj_date(self):
                valueago, valueunit, _ = CleanText('./td/table/tr/td[5]/span[@class="attr_val"]')(self).split()
                delta = timedelta(**{valueunit: float(valueago)})
                return datetime.now() - delta

            def obj_size(self):
                value, unit = CleanText('./td/table/tr/td[2]/span[@class="attr_val"]')(self).split()
                return get_bytes_size(float(value), unit)


class TorrentPage(HTMLPage):
    @method
    class get_torrent(ItemElement):
        klass = Torrent
        ROOT = '//table[@class="torrent_info_tbl"]'

        obj_id = Regexp(CleanText(ROOT + '/tr[3]/td[2]/a/@href'),  r'urn:btih:([0-9a-f]+)', '\\1')
        obj_name = CleanText(ROOT + '/tr[4]/td[2]')
        obj_magnet = CleanText(ROOT + '/tr[3]/td[2]/a/@href')

        def obj_files(self):
            return [_.text for _ in self.xpath(self.ROOT + '/tr[position() > 15]/td[2]')]

        def obj_date(self):
            valueago, valueunit, _ = CleanText(self.ROOT + '/tr[7]/td[2]')(self).split()
            delta = timedelta(**{valueunit: float(valueago)})
            return datetime.now() - delta

        def obj_size(self):
            value, unit = CleanText(self.ROOT + '/tr[6]/td[2]')(self).split()
            return get_bytes_size(float(value), unit)

    def get_torrent_file(self):
        raise MagnetOnly(self.get_torrent().magnet)
