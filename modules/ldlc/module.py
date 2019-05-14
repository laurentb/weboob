# -*- coding: utf-8 -*-

# Copyright(C) 2015      Vincent Paredes
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from weboob.capabilities.bill import CapDocument, Bill
from weboob.capabilities.base import empty
from weboob.tools.backend import AbstractModule, BackendConfig
from weboob.tools.value import ValueBackendPassword, Value

from .browser import LdlcParBrowser, LdlcProBrowser


__all__ = ['LdlcModule']


class LdlcModule(AbstractModule, CapDocument):
    NAME = 'ldlc'
    DESCRIPTION = 'ldlc website'
    MAINTAINER = 'Vincent Paredes'
    EMAIL = 'vparedes@budget-insight.com'
    LICENSE = 'LGPLv3+'
    VERSION = '1.6'
    CONFIG = BackendConfig(Value('login', label='Email'),
                           ValueBackendPassword('password', label='Password'),
                           Value('website', label='Site web', default='part',
                                 choices={'pro': 'Professionnels', 'part': 'Particuliers'}))

    PARENT = 'materielnet'

    def create_default_browser(self):
        if self.config['website'].get() == 'part':
            self.BROWSER = LdlcParBrowser
            return self.create_browser(self.config['login'].get(), self.config['password'].get(), weboob=self.weboob)
        else:
            self.BROWSER = LdlcProBrowser
            return self.create_browser(self.config['login'].get(), self.config['password'].get())

    def download_document(self, bill):
        if not isinstance(bill, Bill):
            bill = self.get_document(bill)
        if empty(bill.url):
            return
        if self.config['website'].get() == 'part':
            return self.browser.open(bill.url).content
        else:
            return self.browser.download_document(bill)
