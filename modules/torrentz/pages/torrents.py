# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from urllib import quote_plus

from weboob.tools.misc import get_bytes_size
from weboob.browser.pages import HTMLPage
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.torrent import Torrent, MagnetOnly
from weboob.browser.filters.standard import CleanText, CleanDecimal, Regexp, Date, Type


class TorrentsPage(HTMLPage):
    @method
    class iter_torrents(ListElement):
        item_xpath = '//div[@class="results"]/dl[count(dt/a) > 0]'

        class item(ItemElement):
            klass = Torrent

            obj_id = Regexp(CleanText('./dt/a/@href'), r'/([0-9a-f]+)', '\\1')
            obj_name = CleanText('./dt/a')
            obj_date = CleanText('./dd/span[@class="a"]/span/@title') & Date(default=None)
            obj_seeders = CleanText('./dd/span[@class="u"]', replace=[(',', '')]) & Type(type=int)
            obj_leechers = CleanText('./dd/span[@class="d"]', replace=[(',', '')]) & Type(type=int)

            def obj_size(self):
                data = CleanText('./dd/span[@class="s"]')(self)
                if data:
                    value, unit = data.split()
                    return get_bytes_size(float(value), unit)
                else:
                    return float("NaN")


class TorrentPage(HTMLPage):
    @method
    class get_torrent(ItemElement):
        klass = Torrent

        obj_id = Regexp(CleanText('//div[@class="trackers"]/div'),  r'info_hash: ([0-9a-f]+)', '\\1')
        obj_name = CleanText('//div[@class="download"]/h2/span')
        obj_date = Date(CleanText('//div[@class="download"]/div/span/@title'))
        obj_size = CleanText('//div[@class="files"]/div/@title', replace=[(',', ''), ('b', '')]) & \
            Type(type=float)

        def obj_seeders(self):
            try:
                return max([int(_.text.replace(',','')) for _ in self.xpath('//div[@class="trackers"]/dl/dd/span[@class="u"]')])
            except ValueError:
                return NotAvailable

        def obj_leechers(self):
            try:
                return max([int(_.text.replace(',','')) for _ in self.xpath('//div[@class="trackers"]/dl/dd/span[@class="d"]')])
            except ValueError:
                return NotAvailable

        def obj_url(self):
            return self.page.browser.BASEURL + \
                Regexp(CleanText('//div[@class="trackers"]/div'), r'info_hash: ([0-9a-f]+)', '\\1')(self)

        def obj_files(self):
            def traverse_nested_lists(ul, result, depth=0):
                for li in ul.xpath('./li'):
                    sub_uls = li.xpath('./ul')
                    if sub_uls:
                        for sub_ul in sub_uls:
                            traverse_nested_lists(sub_ul, result, depth+1)
                    else:
                        result.append(("| " * depth) + li.text_content())

            result = []
            traverse_nested_lists(self.xpath('//div[@class="files"]/ul')[0], result)
            return result

        def obj_magnet(self):
            hsh = Regexp(CleanText('//div[@class="trackers"]/div'),  r'info_hash: ([0-9a-f]+)', '\\1')(self)
            name = "dn=%s" % quote_plus(CleanText('//div[@class="download"]/h2/span')(self))
            trackers = ["tr=%s" % _.text for _ in self.xpath('//div[@class="trackers"]/dl/dt/a')]
            return "&".join(["magnet:?xt=urn:btih:%s" % hsh, name] + trackers)

        def obj_description(self):
            return u"Torrent files available at:\n" + \
                   u"\n\n".join(self.xpath('//div[@class="download"]/dl/dt/a[@rel="e"]/@href'))

    def get_torrent_file(self):
        raise MagnetOnly(self.get_torrent().magnet)
