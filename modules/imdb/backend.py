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

from weboob.capabilities.cinema import ICapCinema
from weboob.tools.backend import BaseBackend

from .browser import ImdbBrowser

from urllib import quote_plus

__all__ = ['ImdbBackend']


class ImdbBackend(BaseBackend, ICapCinema):
    NAME = 'imdb'
    MAINTAINER = u'Julien Veyssier'
    EMAIL = 'julien.veyssier@aiur.fr'
    VERSION = '0.f'
    DESCRIPTION = 'Internet Movie Database service'
    LICENSE = 'AGPLv3+'
    BROWSER = ImdbBrowser

    def create_default_browser(self):
        return self.create_browser()

    def get_movie(self, id):
        return self.browser.get_movie(id)

    def get_person(self, id):
        return self.browser.get_person(id)

    def iter_movies(self, pattern):
        return self.browser.iter_movies(quote_plus(pattern.encode('utf-8')))

    def iter_persons(self, pattern):
        return self.browser.iter_persons(quote_plus(pattern.encode('utf-8')))

    def iter_movie_persons(self, id):
        return self.browser.iter_movie_persons(id)

    def iter_person_movies(self, id):
        return self.browser.iter_person_movies(id)
