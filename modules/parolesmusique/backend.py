# -*- coding: utf-8 -*-

# Copyright(C) 2013 Julien Veyssier
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

from weboob.capabilities.lyrics import ICapLyrics
from weboob.tools.backend import BaseBackend

from .browser import ParolesmusiqueBrowser

from urllib import quote_plus

__all__ = ['ParolesmusiqueBackend']


class ParolesmusiqueBackend(BaseBackend, ICapLyrics):
    NAME = 'parolesmusique'
    MAINTAINER = u'Julien Veyssier'
    EMAIL = 'julien.veyssier@aiur.fr'
    VERSION = '0.f'
    DESCRIPTION = 'paroles-musique lyrics website'
    LICENSE = 'AGPLv3+'
    BROWSER = ParolesmusiqueBrowser

    def create_default_browser(self):
        return self.create_browser()

    def get_lyrics(self, id):
        return self.browser.get_lyrics(id)

    def iter_lyrics(self, criteria, pattern):
        return self.browser.iter_lyrics(criteria,pattern.encode('utf-8'))
