# -*- coding: utf-8 -*-

# Copyright(C) 2010-2013  Romain Bignon, Pierre Mazière
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
import re

from weboob.capabilities.bank import CapBankTransferAddRecipient, AccountNotFound, \
                                     RecipientNotFound, TransferError, Account
from weboob.capabilities.contact import CapContact
from weboob.capabilities.profile import CapProfile
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.capabilities.bank.transactions import sorted_transactions
from weboob.tools.value import ValueBackendPassword, Value
from weboob.capabilities.base import find_object

from .browser import LCLBrowser, LCLProBrowser, ELCLBrowser
from .enterprise.browser import LCLEnterpriseBrowser, LCLEspaceProBrowser


__all__ = ['LCLModule']


class LCLModule(Module, CapBankTransferAddRecipient, CapContact, CapProfile):
    NAME = 'lcl'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.3'
    DESCRIPTION = u'LCL'
    LICENSE = 'AGPLv3+'
    CONFIG = BackendConfig(ValueBackendPassword('login',    label='Identifiant', masked=False),
                           ValueBackendPassword('password', label='Code personnel'),
                           Value('website', label='Type de compte', default='par',
                                 choices={'par': 'Particuliers',
                                          'pro': 'Professionnels',
                                          'ent': 'Entreprises',
                                          'esp': 'Espace Pro',
                                          'elcl': 'e.LCL'}))
    BROWSER = LCLBrowser

    def create_default_browser(self):
        # assume all `website` option choices are defined here
        browsers = {'par': LCLBrowser,
                    'pro': LCLProBrowser,
                    'elcl': ELCLBrowser,
                    'ent': LCLEnterpriseBrowser,
                    'esp': LCLEspaceProBrowser}

        website_value = self.config['website']
        self.BROWSER = browsers.get(website_value.get(),
                                    browsers[website_value.default])

        return self.create_browser(self.config['login'].get(),
                                   self.config['password'].get())

    def iter_accounts(self):
        return self.browser.get_accounts_list()

    def get_account(self, _id):
        return find_object(self.browser.get_accounts_list(), id=_id, error=AccountNotFound)

    def iter_coming(self, account):
        transactions = sorted_transactions(self.browser.get_cb_operations(account))
        return transactions

    def iter_history(self, account):
        transactions = sorted_transactions(self.browser.get_history(account))
        return transactions

    def iter_investment(self, account):
        return self.browser.get_investment(account)

    def iter_transfer_recipients(self, origin_account):
        if self.config['website'].get() not in  ['par', 'pro', 'elcl']:
            raise NotImplementedError()
        if not isinstance(origin_account, Account):
            origin_account = find_object(self.iter_accounts(), id=origin_account, error=AccountNotFound)
        return self.browser.iter_recipients(origin_account)

    def new_recipient(self, recipient, **params):
        if self.config['website'].get() not in  ['par', 'pro']:
            raise NotImplementedError()
        # Recipient label has max 15 alphanumrical chars.
        recipient.label = ' '.join(w for w in re.sub('[^0-9a-zA-Z ]+', '', recipient.label).split())[:15]
        return self.browser.new_recipient(recipient, **params)

    def init_transfer(self, transfer, **params):
        if self.config['website'].get() not in  ['par', 'pro']:
            raise NotImplementedError()

        # There is a check on the website, transfer can't be done with too long reason.
        if transfer.label:
            transfer.label = transfer.label[:30]

        self.logger.info('Going to do a new transfer')
        if transfer.account_iban:
            account = find_object(self.iter_accounts(), iban=transfer.account_iban, error=AccountNotFound)
        else:
            account = find_object(self.iter_accounts(), id=transfer.account_id, error=AccountNotFound)

        if transfer.recipient_iban:
            recipient = find_object(self.iter_transfer_recipients(account.id), iban=transfer.recipient_iban, error=RecipientNotFound)
        else:
            recipient = find_object(self.iter_transfer_recipients(account.id), id=transfer.recipient_id, error=RecipientNotFound)

        try:
            # quantize to show 2 decimals.
            amount = Decimal(transfer.amount).quantize(Decimal(10) ** -2)
        except (AssertionError, ValueError):
            raise TransferError('something went wrong')

        return self.browser.init_transfer(account, recipient, amount, transfer.label)

    def execute_transfer(self, transfer, **params):
        return self.browser.execute_transfer(transfer)

    def iter_contacts(self):
        if self.config['website'].get() != "par":
            raise NotImplementedError()

        return self.browser.get_advisor()

    def get_profile(self):
        if not hasattr(self.browser, 'get_profile'):
            raise NotImplementedError()
        return self.browser.get_profile()
