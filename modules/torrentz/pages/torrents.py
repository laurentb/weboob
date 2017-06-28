# -*- coding: utf-8 -*-

from datetime import datetime

from weboob.tools.misc import get_bytes_size
from weboob.browser.pages import HTMLPage
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.torrent import Torrent, MagnetOnly
from weboob.browser.filters.standard import CleanText, Regexp, Date, Type
from weboob.tools.compat import quote_plus


def parse_timestamp(txt, **kwargs):
    try:
        ts = int(txt)
        return datetime.fromtimestamp(ts)
    except:
        return None


class TorrentsPage(HTMLPage):
    @method
    class iter_torrents(ListElement):
        item_xpath = '//div[@class="results"]/dl[count(dt/a) > 0]'

        class item(ItemElement):
            klass = Torrent

            obj_id = Regexp(CleanText('./dt/a/@href'), r'/([0-9a-f]+)', '\\1')
            obj_name = CleanText('./dt/a')
            obj_date = CleanText('./dd/span[2]/@title') & Date(default=None, parse_func=parse_timestamp)
            obj_seeders = CleanText('./dd/span[4]', replace=[(',', '')]) & Type(type=int)
            obj_leechers = CleanText('./dd/span[5]', replace=[(',', '')]) & Type(type=int)

            def obj_size(self):
                data = CleanText('./dd/span[3]')(self)
                if data:
                    value, unit = data.split()
                    return get_bytes_size(float(value), unit)
                else:
                    return float("NaN")


class TorrentPage(HTMLPage):
    @method
    class get_torrent(ItemElement):
        klass = Torrent

        obj_id = Regexp(CleanText('//div[@class="trackers"]/h2'),  r'hash ([0-9a-f]+)', '\\1')
        obj_name = CleanText('//div[@class="downlinks"]/h2/span')
        obj_date = CleanText('//div[@class="downlinks"]/div/span/@title') & Date(default=None)
        obj_size = CleanText('//div[@class="files"]/div/@title', replace=[(',', ''), ('b', '')]) & \
            Type(type=float)

        def obj_seeders(self):
            try:
                return max([int(_.text.replace(',', ''))
                            for _ in self.xpath('//div[@class="trackers"]/dl/dd/span[@class="u"]')])
            except ValueError:
                return NotAvailable

        def obj_leechers(self):
            try:
                return max([int(_.text.replace(',', ''))
                            for _ in self.xpath('//div[@class="trackers"]/dl/dd/span[@class="d"]')])
            except ValueError:
                return NotAvailable

        def obj_url(self):
            return self.page.browser.BASEURL + \
                Regexp(CleanText('//div[@class="trackers"]/h2'), r'hash ([0-9a-f]+)', '\\1')(self)

        def obj_files(self):
            def traverse_nested_lists(ul, result, depth=0):
                for li in ul.xpath('./li'):
                    sub_uls = li.xpath('./ul')
                    if sub_uls:
                        result.append(("| " * depth) + ("%s" % li.text))
                        for sub_ul in sub_uls:
                            traverse_nested_lists(sub_ul, result, depth+1)
                    else:
                        try:
                            size = li.xpath('span')[0].text
                        except:
                            size = ""
                        result.append(("| " * depth) + ("%s [%s]" % (li.text, size)))

            result = []
            traverse_nested_lists(self.xpath('//div[@class="files"]/ul')[0], result)
            return result

        def obj_magnet(self):
            hsh = Regexp(CleanText('//div[@class="trackers"]/h2'),  r'hash ([0-9a-f]+)', '\\1')(self)
            name = "dn=%s" % quote_plus(CleanText('//div[@class="downlinks"]/h2/span')(self))
            trackers = ["tr=%s" % _.text for _ in self.xpath('//div[@class="trackers"]/dl/dt')]
            return "&".join(["magnet:?xt=urn:btih:%s" % hsh, name] + trackers)

        def obj_description(self):
            return u"Torrent files available at:\n" + \
                   u"\n\n".join(self.xpath('//div[@class="downlinks"]/dl/dt/a/@href'))

    def get_torrent_file(self):
        raise MagnetOnly(self.get_torrent().magnet)
