# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Julien Veyssier
# Copyright(C) 2012-2013 Romain Bignon
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



from decimal import Decimal
import string

from weboob.capabilities.bank import ICapBank, AccountNotFound, Recipient, Account
from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.tools.value import ValueBackendPassword

from .browser import CreditMutuelBrowser


__all__ = ['CreditMutuelBackend']


class CreditMutuelBackend(BaseBackend, ICapBank):
    NAME = 'creditmutuel'
    MAINTAINER = u'Julien Veyssier'
    EMAIL = 'julien.veyssier@aiur.fr'
    VERSION = '0.j'
    DESCRIPTION = u'Crédit Mutuel'
    LICENSE = 'AGPLv3+'
    CONFIG = BackendConfig(ValueBackendPassword('login',    label='Identifiant', regexp='^\d{1,13}\w$', masked=False),
                           ValueBackendPassword('password', label='Mot de passe'))
    BROWSER = CreditMutuelBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(), self.config['password'].get())

    def iter_accounts(self):
        for account in self.browser.get_accounts_list():
            yield account

    def get_account(self, _id):
        account = self.browser.get_account(_id)
        if account:
            return account
        else:
            raise AccountNotFound()

    def iter_coming(self, account):
        for tr in self.browser.get_history(account):
            if tr._is_coming:
                yield tr

    def iter_history(self, account):
        for tr in self.browser.get_history(account):
            if not tr._is_coming:
                yield tr

    def iter_transfer_recipients(self, ignored):
        for account in self.browser.get_accounts_list():
            recipient = Recipient()
            recipient.id = account.id
            recipient.label = account.label
            yield recipient

    def transfer(self, account, to, amount, reason=None):
        if isinstance(account, Account):
            account = account.id

        account = str(account).strip(string.letters)
        to = str(to).strip(string.letters)
        try:
            assert account.isdigit()
            assert to.isdigit()
            amount = Decimal(amount)
        except (AssertionError, ValueError):
            raise AccountNotFound()

        with self.browser:
            return self.browser.transfer(account, to, amount, reason)
