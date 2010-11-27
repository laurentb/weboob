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


from weboob.tools.browser import BaseBrowser

from .pages.torrents import TorrentsPage, TorrentPage


__all__ = ['IsohuntBrowser']


class IsohuntBrowser(BaseBrowser):
    DOMAIN = 'isohunt.com'
    PROTOCOL = 'https'
    ENCODING = 'utf-8'
    USER_AGENT = BaseBrowser.USER_AGENTS['wget']
    PAGES = {
             'https://isohunt.com/torrents/.*iht=-1&ihp=1&ihs1=2&iho1=d' : TorrentsPage,
             'http://isohunt.com/torrent_details.*tab=summary' : TorrentPage
             }

    def __init__(self, *args, **kwargs):
        BaseBrowser.__init__(self, *args, **kwargs)

    def home(self):
        return self.location('https://isohunt.com')

    def iter_torrents(self, pattern):
        self.location('https://isohunt.com/torrents/%s?iht=-1&ihp=1&ihs1=2&iho1=d' % pattern)

        assert self.is_on_page(TorrentsPage)
        return self.page.iter_torrents()

    def get_torrent(self, id):
        self.location('https://isohunt.com/torrent_details/%s/?tab=summary' % id)

        assert self.is_on_page(TorrentPage)
        return self.page.get_torrent(id)
