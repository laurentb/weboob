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

from weboob.tools.backend import Module, BackendConfig
from weboob.capabilities.library import CapBook
from weboob.tools.value import Value, ValueBackendPassword

from .browser import BibliothequesparisBrowser


__all__ = ['BibliothequesparisModule']


class BibliothequesparisModule(Module, CapBook):
    NAME = 'bibliothequesparis'
    DESCRIPTION = u'Bibliotheques de Paris'
    MAINTAINER = u'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '2.1'

    BROWSER = BibliothequesparisBrowser

    CONFIG = BackendConfig(
        Value('login', label='Library card number'),
        ValueBackendPassword('password', label='Password (usually birthdate)'),
    )

    def create_default_browser(self, *args, **kwargs):
        return self.create_browser(self.config['login'].get(), self.config['password'].get(), *args, **kwargs)

    def iter_rented(self):
        return self.browser.get_loans()

    def get_book(self, _id):
        raise NotImplementedError()

    def iter_booked(self):
        raise NotImplementedError()

    def iter_books(self):
        raise NotImplementedError()

    def renew_book(self, _id):
        return self.browser.do_renew(_id)

    def search_books(self, pattern):
        return self.browser.search_books(pattern)
