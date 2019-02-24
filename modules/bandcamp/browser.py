# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from weboob.browser import PagesBrowser, URL

from .pages import ReleasesPage, SearchPage, AlbumsPage, AlbumPage, TrackPage


class BandcampBrowser(PagesBrowser):
    BASEURL = 'https://bandcamp.com'

    search = URL(r'/search\?(?:page=\d+&)?q=(?P<q>.*)',
                 SearchPage)
    releases = URL(r'https://(?P<band>[^.]+).bandcamp.com/releases', ReleasesPage)
    albums = URL(r'https://(?P<band>[^.]+).bandcamp.com/music', AlbumsPage)
    album = URL(r'https://(?P<band>[^.]+).bandcamp.com/album/(?P<album>[^/]+)', AlbumPage)
    track = URL(r'https://(?P<band>[^.]+).bandcamp.com/track/(?P<track>[^/]+)', TrackPage)

    def do_search(self, pattern):
        self.search.go(q=pattern)

        for a in self.page.iter_content():
            if a.id is not None:
                yield a

    def fetch_album(self, album):
        self.location(album.url)
        return self._fetch_album()

    def fetch_album_by_id(self, band, name):
        self.album.go(band=band, album=name)
        return self._fetch_album()

    def _fetch_album(self):
        album = self.page.get_album()
        album.tracks_list = list(self.page.iter_tracks())
        for tr, extra in zip(album.tracks_list, self.page.get_tracks_extra()):
            tr.url = extra['url']
            tr.duration = extra['duration']
        return album

    def fetch_track(self, track):
        self.location(track._page_url)
        return self.page.get_track()

    def fetch_track_by_id(self, band, name):
        self.track.go(band=band, track=name)
        return self.page.get_track()
