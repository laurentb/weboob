# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012  Jeremy Monnet
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


from weboob.capabilities.library import CapBook
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword, Value

from .browser import AloesBrowser


__all__ = ['AloesModule']


class AloesModule(Module, CapBook):
    NAME = 'opacwebaloes'
    MAINTAINER = u'Jeremy Monnet'
    EMAIL = 'jmonnet@gmail.com'
    VERSION = '1.3'
    DESCRIPTION = 'Aloes Library software'
    LICENSE = 'AGPLv3+'
    CONFIG = BackendConfig(Value('login',    label='Account ID', regexp='^\d{1,8}\w$'),
                           ValueBackendPassword('password', label='Password of account'),
                           Value('baseurl',    label='Base URL')
                           )
    BROWSER = AloesBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['baseurl'].get(),
                                   self.config['login'].get(),
                                   self.config['password'].get())

    def iter_rented(self):
        for book in self.browser.get_rented_books_list():
            yield book

    def iter_booked(self):
        for book in self.browser.get_booked_books_list():
            yield book

    def iter_books(self):
        for book in self.iter_booked():
            yield book
        for book in self.iter_rented():
            yield book

    def get_book(self, _id):
        raise NotImplementedError()

    def search_books(self, _string):
        raise NotImplementedError()
