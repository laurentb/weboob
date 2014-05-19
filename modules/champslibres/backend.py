# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Florent Fourcot
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


from weboob.capabilities.library import ICapBook
from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.tools.value import ValueBackendPassword, Value

from .browser import ChampslibresBrowser


__all__ = ['ChampslibresBackend']


class ChampslibresBackend(BaseBackend, ICapBook):
    NAME = 'champslibres'
    MAINTAINER = u'Florent Fourcot'
    EMAIL = 'weboob@flo.fourcot.fr'
    VERSION = '0.j'
    DESCRIPTION = 'Champs Libres (Rennes) Library'
    LICENSE = 'AGPLv3+'
    CONFIG = BackendConfig(Value('login', label='Account ID', regexp='^\d{1,15}|$'),
                           ValueBackendPassword('password', label='Password of account'),
                           )
    BROWSER = ChampslibresBrowser

    def create_default_browser(self):
        browser = self.create_browser(self.config['login'].get(),
                                   self.config['password'].get())
        # we have to force the login before to lauch any actions
        browser.login()
        return browser

    def get_rented(self):
        for book in self.browser.get_rented_books_list():
            yield book

    def get_booked(self):
        raise NotImplementedError()

    def renew_book(self, id):
        return self.browser.renew(id)

    def iter_books(self):
        #for book in self.get_booked():
        #    yield book
        for book in self.get_rented():
            yield book

    def get_book(self, _id):
        raise NotImplementedError()

    def search_books(self, _string):
        raise NotImplementedError()
