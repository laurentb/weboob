# -*- coding: utf-8 -*-

# Copyright(C) 2012-2013 Romain Bignon
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

from weboob.capabilities.bank import CapBankTransfer, CapBankWealth, Account, AccountNotFound, RecipientNotFound
from weboob.capabilities.contact import CapContact
from weboob.capabilities.base import find_object, strict_find_object
from weboob.capabilities.profile import CapProfile
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value, ValueBackendPassword

from .par.browser import CmsoParBrowser
from .pro.browser import CmsoProBrowser


__all__ = ['CmsoModule']


class CmsoModule(Module, CapBankTransfer, CapBankWealth, CapContact, CapProfile):
    NAME = 'cmso'
    MAINTAINER = 'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '2.0'
    DESCRIPTION = 'Crédit Mutuel Sud-Ouest'
    LICENSE = 'LGPLv3+'
    CONFIG = BackendConfig(ValueBackendPassword('login',    label='Identifiant', masked=False),
                           ValueBackendPassword('password', label='Mot de passe'),
                           Value('website', label='Type de compte', default='par',
                                 choices={'par': 'Particuliers', 'pro': 'Professionnels'}))

    BROWSER = CmsoParBrowser

    def create_default_browser(self):
        b = {'par': CmsoParBrowser, 'pro': CmsoProBrowser}
        self.BROWSER = b[self.config['website'].get()]
        return self.create_browser("%s.%s" % (self.NAME, 'com' if self.NAME == 'cmso' else 'fr'),
                                   self.config['login'].get(),
                                   self.config['password'].get())

    def get_account(self, _id):
        return find_object(self.browser.iter_accounts(), id=_id, error=AccountNotFound)

    def iter_accounts(self):
        return self.browser.iter_accounts()

    def iter_history(self, account):
        return self.browser.iter_history(account)

    def iter_coming(self, account):
        return self.browser.iter_coming(account)

    def iter_investment(self, account):
        return self.browser.iter_investment(account)

    def iter_transfer_recipients(self, origin_account):
        if self.config['website'].get() != "par":
            raise NotImplementedError()

        if not isinstance(origin_account, Account):
            origin_account = self.get_account(origin_account)
        return self.browser.iter_recipients(origin_account)

    def init_transfer(self, transfer, **params):
        if self.config['website'].get() != "par":
            raise NotImplementedError()

        self.logger.info('Going to do a new transfer')

        account = strict_find_object(
            self.iter_accounts(),
            error=AccountNotFound,
            iban=transfer.account_iban,
            id=transfer.account_id
        )

        recipient = strict_find_object(
            self.iter_transfer_recipients(account.id),
            error=RecipientNotFound,
            iban=transfer.recipient_iban,
            id=transfer.recipient_id
        )

        return self.browser.init_transfer(account, recipient, transfer.amount, transfer.label, transfer.exec_date)

    def execute_transfer(self, transfer, **params):
        return self.browser.execute_transfer(transfer, **params)

    def iter_contacts(self):
        if self.config['website'].get() != "par":
            raise NotImplementedError()

        return self.browser.get_advisor()

    def get_profile(self):
        return self.browser.get_profile()
