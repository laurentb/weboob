# -*- coding: utf-8 -*-

# Copyright(C) 2010-2017 Julien Veyssier, Laurent Bachelier
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


from weboob.browser import URL, PagesBrowser

from .pages.index import IndexPage
from .pages.torrents import FilesPage, TorrentPage, TorrentsPage

__all__ = ['PiratebayBrowser']


class PiratebayBrowser(PagesBrowser):
    BASEURL = 'https://thepiratebay.org/'

    index_page = URL('$', IndexPage)
    torrents_page = URL('search/(?P<query>.+)/0/7/0', TorrentsPage)
    torrent_page = URL('torrent/(?P<id>.+)', TorrentPage)
    files_page = URL('ajax_details_filelist\.php\?id=(?P<id>.+)', FilesPage)

    def iter_torrents(self, pattern):
        self.torrents_page.go(query=pattern)
        return self.page.iter_torrents()

    def get_torrent(self, _id):
        self.torrent_page.go(id=_id)
        torrent = self.page.get_torrent()
        self.files_page.go(id=_id)
        files = self.page.get_files()
        torrent.files = files
        return torrent
