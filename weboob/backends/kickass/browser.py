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


__all__ = ['KickassBrowser']


class KickassBrowser(BaseBrowser):
    DOMAIN = 'kickasstorrents.com'
    PROTOCOL = 'http'
    ENCODING = 'utf-8'
    USER_AGENT = BaseBrowser.USER_AGENTS['wget']
    PAGES = {
             'http://fr.kickasstorrents.com/new/.*field=seeders&sorder=desc' : TorrentsPage,
             'http://fr.kickasstorrents.com/.*.html' : TorrentPage
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
        return self.location('http://kickasstorrents.com')

    def iter_torrents(self, pattern):
        #self.location(self.buildurl('/torrents.php', searchstr=pattern))
        self.location('http://fr.kickasstorrents.com/new/?q=%s&field=seeders&sorder=desc' % pattern)

        assert self.is_on_page(TorrentsPage)
        return self.page.iter_torrents()

    def get_torrent(self, id):
        self.location('http://fr.kickasstorrents.com/%s.html' % id)

        assert self.is_on_page(TorrentPage)
        return self.page.get_torrent(id)
