# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Julien Veyssier
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


from weboob.capabilities.bank import ICapBank, AccountNotFound
from weboob.tools.backend import BaseBackend
from weboob.tools.value import ValuesDict, Value

from .browser import CreditMutuelBrowser


__all__ = ['CreditMutuelBackend']


class CreditMutuelBackend(BaseBackend, ICapBank):
    NAME = 'creditmutuel'
    MAINTAINER = 'Julien Veyssier'
    EMAIL = 'julien.veyssier@aiur.fr'
    VERSION = '0.8.4'
    DESCRIPTION = u'Crédit Mutuel french bank'
    LICENSE = 'AGPLv3+'
    CONFIG = ValuesDict(Value('login',    label='Account ID', regexp='^\d{1,13}\w$'),
                        Value('password', label='Password of account', masked=True))
    BROWSER = CreditMutuelBrowser

    def create_default_browser(self):
        return self.create_browser( self.config['login'], self.config['password'])

    def iter_accounts(self):
        for account in self.browser.get_accounts_list():
            yield account

    def get_account(self, _id):
        if not _id.isdigit():
            raise AccountNotFound()
        account = self.browser.get_account(_id)
        if account:
            return account
        else:
            raise AccountNotFound()

    def iter_operations(self, account):
        """ TODO Not supported yet """
        return iter([])

    def iter_history(self, account):
        for history in self.browser.get_history(account):
            yield history
