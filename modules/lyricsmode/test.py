# -*- coding: utf-8 -*-

# Copyright(C) 2016 Julien Veyssier
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

from weboob.tools.test import BackendTest
from weboob.capabilities.base import NotLoaded


class LyricsmodeTest(BackendTest):
    MODULE = 'lyricsmode'

    def test_search_song_n_get(self):
        l_lyrics = list(self.backend.iter_lyrics('song', 'chien'))
        for songlyrics in l_lyrics:
            assert songlyrics.id
            assert songlyrics.title
            assert songlyrics.artist
            assert songlyrics.content is NotLoaded
            full_lyr = self.backend.get_lyrics(songlyrics.id)
            assert full_lyr.id
            assert full_lyr.title
            assert full_lyr.artist
            assert full_lyr.content is not NotLoaded

    def test_search_artist(self):
        l_lyrics = list(self.backend.iter_lyrics('artist', 'boris'))
        for songlyrics in l_lyrics:
            assert songlyrics.id
            assert songlyrics.title
            assert songlyrics.artist
            assert songlyrics.content is NotLoaded
