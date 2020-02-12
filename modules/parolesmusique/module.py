# -*- coding: utf-8 -*-

# Copyright(C) 2016 Julien Veyssier
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

from weboob.capabilities.lyrics import CapLyrics, SongLyrics
from weboob.tools.backend import Module

from .browser import ParolesmusiqueBrowser

__all__ = ['ParolesmusiqueModule']


class ParolesmusiqueModule(Module, CapLyrics):
    NAME = 'parolesmusique'
    MAINTAINER = u'Julien Veyssier'
    EMAIL = 'eneiluj@gmx.fr'
    VERSION = '2.1'
    DESCRIPTION = 'paroles-musique lyrics website'
    LICENSE = 'AGPLv3+'
    BROWSER = ParolesmusiqueBrowser

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
