# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon, Pierre Mazière
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


from __future__ import with_statement

from weboob.capabilities.bank import ICapBank, AccountNotFound
from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.tools.value import ValueBackendPassword, Value

from .browser import LCLBrowser


__all__ = ['LCLBackend']


class LCLBackend(BaseBackend, ICapBank):
    NAME = 'lcl'
    MAINTAINER = u'Pierre Mazière'
    EMAIL = 'pierre.maziere@gmail.com'
    VERSION = '0.9'
    DESCRIPTION = 'Le Credit Lyonnais crappy french bank'
    LICENSE = 'AGPLv3+'
    CONFIG = BackendConfig(ValueBackendPassword('login',    label='Account ID', regexp='^\d{1,6}\w$', masked=False),
                           ValueBackendPassword('password', label='Password of account'),
                           Value('agency',   label='Agency code', regexp='^\d{3,4}$'))
    BROWSER = LCLBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['agency'].get(),
                                   self.config['login'].get(),
                                   self.config['password'].get())

    def iter_accounts(self):
        for account in self.browser.get_accounts_list():
            yield account

    def get_account(self, _id):
        with self.browser:
            account = self.browser.get_account(_id)
        if account:
            return account
        else:
            raise AccountNotFound()

    def iter_operations(self, account):
        """ TODO Not supported yet """
        return iter([])

    def iter_history(self, account):
        with self.browser:
            for history in self.browser.get_history(account):
                yield history

