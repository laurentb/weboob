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


from weboob.tools.browser import BaseBrowser

from .pages.index import IndexPage
from .pages.torrents import TorrentsPage, TorrentPage


__all__ = ['PiratebayBrowser']


class PiratebayBrowser(BaseBrowser):
    DOMAIN = 'thepiratebay.org'
    PROTOCOL = 'https'
    ENCODING = 'utf-8'
    USER_AGENT = BaseBrowser.USER_AGENTS['wget']
    PAGES = {'https://thepiratebay.org' : IndexPage,
             'https://thepiratebay.org/search/.*/0/7/0' : TorrentsPage,
             'https://thepiratebay.org/torrent/.*' : TorrentPage
             }

    def __init__(self, *args, **kwargs):
        #self.DOMAIN = domain
        #self.PROTOCOL = protocol
        #self.PAGES = {}
        #for key, value in PiratebayBrowser.PAGES.iteritems():
        #    self.PAGES[key % domain] = value

        BaseBrowser.__init__(self, *args, **kwargs)

    #def login(self):
    #    if not self.is_on_page(LoginPage):
    #        self.home()
    #    self.page.login(self.username, self.password)

    #def is_logged(self):
    #    if not self.page or self.is_on_page(LoginPage):
    #        return False
    #    if self.is_on_page(IndexPage):
    #        return self.page.is_logged()
    #    return True

    def home(self):
        return self.location('https://thepiratebay.org')

    def iter_torrents(self, pattern):
        #self.location(self.buildurl('/torrents.php', searchstr=pattern))
        self.location('https://thepiratebay.org/search/%s/0/7/0' % pattern)

        assert self.is_on_page(TorrentsPage)
        return self.page.iter_torrents()

    def get_torrent(self, id):
        self.location('https://thepiratebay.org/torrent/%s/' % id)

        assert self.is_on_page(TorrentPage)
        return self.page.get_torrent(id)
