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

from weboob.capabilities.lyrics import CapLyrics, SongLyrics
from weboob.tools.backend import Module

from .browser import LyricsplanetBrowser

__all__ = ['LyricsplanetModule']


class LyricsplanetModule(Module, CapLyrics):
    NAME = 'lyricsplanet'
    MAINTAINER = u'Julien Veyssier'
    EMAIL = 'eneiluj@gmx.fr'
    VERSION = '1.4'
    DESCRIPTION = 'Lyricsplanet.com song lyrics website'
    LICENSE = 'AGPLv3+'
    BROWSER = LyricsplanetBrowser

    def get_lyrics(self, id):
        return self.browser.get_lyrics(id)

    def iter_lyrics(self, criteria, pattern):
        return self.browser.iter_lyrics(criteria, pattern.encode('utf-8'))

    def fill_songlyrics(self, songlyrics, fields):
        if 'content' in fields:
            sl = self.get_lyrics(songlyrics.id)
            songlyrics.content = sl.content
        return songlyrics

    OBJECTS = {
        SongLyrics: fill_songlyrics
    }
