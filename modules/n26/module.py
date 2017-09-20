# -*- coding: utf-8 -*-

# Copyright(C) 2016      Benjamin Bouvier
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


from weboob.capabilities.bank import CapBank
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value, ValueBackendPassword

from .browser import Number26Browser

__all__ = ['Number26Module']


class Number26Module(Module, CapBank):
    NAME = 'n26'
    DESCRIPTION = u'Bank N26'
    MAINTAINER = u'Benjamin Bouvier'
    EMAIL = 'public@benj.me'
    LICENSE = 'AGPLv3+'
    VERSION = '1.4'

    BROWSER = Number26Browser

    CONFIG = BackendConfig(
                 Value('login', label='Email', regexp='.+'),
                 ValueBackendPassword('password', label='Password')
             )

    STORAGE = {'categories': {}}

    def get_categories(self):
        categories = self.storage.get("categories", None)
        if categories is None:
            categories = self.browser.get_categories()
            self.storage.set("categories", categories)
        return categories

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(), self.config['password'].get())

    def iter_accounts(self):
        return self.browser.get_accounts()

    def get_account(self, id):
        return self.browser.get_account(id)

    def iter_history(self, account):
        categories = self.get_categories()
        return self.browser.get_transactions(categories)

    def iter_coming(self, account):
        categories = self.get_categories()
        return self.browser.get_coming(categories)
