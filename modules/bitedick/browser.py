# -*- coding: utf-8 -*-

import urllib

from weboob.tools.browser import BaseBrowser

from .pages.index import IndexPage
from .pages.torrents import TorrentsPage, TorrentPage


__all__ = ['BTDiggBrowser']


class BTDiggBrowser(BaseBrowser):
    DOMAIN = 'btdigg.org'
    PROTOCOL = 'https'
    ENCODING = 'utf-8'
    USER_AGENT = BaseBrowser.USER_AGENTS['wget']
    PAGES = {'https://btdigg.org/': IndexPage,
             'https://btdigg.org/search?.*q=[^?]*': TorrentsPage,
             'https://btdigg.org/search?.*info_hash=[^?]*': TorrentPage,
             }

    def home(self):
        return self.location('https://btdigg.org')

    def iter_torrents(self, pattern):
        self.location('https://btdigg.org/search?q=%s' % urllib.quote_plus(pattern.encode('utf-8')))

        assert self.is_on_page(TorrentsPage)
        return self.page.iter_torrents()

    def get_torrent(self, id):
        self.location('https://btdigg.org/search?info_hash=%s' % id)

        assert self.is_on_page(TorrentPage)
        return self.page.get_torrent(id)

    def get_torrent_file(self, id):
        self.location('https://btdigg.org/search?info_hash=%s' % id)

        assert self.is_on_page(TorrentPage)
        return self.page.get_torrent_file(id)
