# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Jocelyn Jaubert
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

import re
from decimal import Decimal
from datetime import timedelta

from weboob.capabilities.bank import CapBankWealth, CapBankTransferAddRecipient, AccountNotFound, Account, RecipientNotFound
from weboob.capabilities.contact import CapContact
from weboob.capabilities.profile import CapProfile
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value, ValueBackendPassword
from weboob.capabilities.base import find_object

from .browser import SocieteGenerale
from .sgpe.browser import SGEnterpriseBrowser, SGProfessionalBrowser


__all__ = ['SocieteGeneraleModule']


class SocieteGeneraleModule(Module, CapBankWealth, CapBankTransferAddRecipient, CapContact, CapProfile):
    NAME = 'societegenerale'
    MAINTAINER = u'Jocelyn Jaubert'
    EMAIL = 'jocelyn.jaubert@gmail.com'
    VERSION = '1.4'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u'Société Générale'
    CONFIG = BackendConfig(
        ValueBackendPassword('login',      label='Code client', masked=False),
        ValueBackendPassword('password',   label='Code secret'),
        Value('website', label='Type de compte', default='par',
              choices={'par': 'Particuliers', 'pro': 'Professionnels', 'ent': 'Entreprises'}))

    def create_default_browser(self):
        b = {'par': SocieteGenerale, 'pro': SGProfessionalBrowser, 'ent': SGEnterpriseBrowser}
        self.BROWSER = b[self.config['website'].get()]
        return self.create_browser(self.config['login'].get(),
                                   self.config['password'].get())

    def iter_accounts(self):
        for account in self.browser.get_accounts_list():
            yield account

    def get_account(self, _id):
        return find_object(self.browser.get_accounts_list(), id=_id, error=AccountNotFound)

    def key(self, tr):
        # Can't compare datetime and date, so cast them.
        try:
            return tr.rdate.date()
        except AttributeError:
            return tr.rdate

    def iter_coming(self, account):
        if hasattr(self.browser, 'get_cb_operations'):
            transactions = list(self.browser.get_cb_operations(account))
        else:
            transactions = [tr for tr in self.browser.iter_history(account) if tr._coming]
        transactions.sort(key=self.key, reverse=True)
        return transactions

    def iter_history(self, account):
        if hasattr(self.browser, 'get_cb_operations'):
            transactions = list(self.browser.iter_history(account))
        else:
            transactions = [tr for tr in self.browser.iter_history(account) if not tr._coming]
        transactions.sort(key=self.key, reverse=True)
        return transactions

    def iter_investment(self, account):
        return self.browser.iter_investment(account)

    def iter_contacts(self):
        if not hasattr(self.browser, 'get_advisor'):
            raise NotImplementedError()
        return self.browser.get_advisor()

    def get_profile(self):
        if not hasattr(self.browser, 'get_profile'):
            raise NotImplementedError()
        return self.browser.get_profile()

    def iter_transfer_recipients(self, origin_account):
        if self.config['website'].get() != 'par':
            raise NotImplementedError()
        if not isinstance(origin_account, Account):
            origin_account = find_object(self.iter_accounts(), id=origin_account, error=AccountNotFound)
        return self.browser.iter_recipients(origin_account)

    def new_recipient(self, recipient, **params):
        recipient.label = ' '.join(w for w in re.sub('[^0-9a-zA-Z:\/\-\?\(\)\.,\'\+ ]+', '', recipient.label).split())
        return self.browser.new_recipient(recipient, **params)

    def init_transfer(self, transfer, **params):
        if self.config['website'].get() != 'par':
            raise NotImplementedError()
        transfer.label = ' '.join(w for w in re.sub('[^0-9a-zA-Z ]+', '', transfer.label).split())
        self.logger.info('Going to do a new transfer')
        if transfer.account_iban:
            account = find_object(self.iter_accounts(), iban=transfer.account_iban, error=AccountNotFound)
        else:
            account = find_object(self.iter_accounts(), id=transfer.account_id, error=AccountNotFound)

        if transfer.recipient_iban:
            recipient = find_object(self.iter_transfer_recipients(account.id), iban=transfer.recipient_iban, error=RecipientNotFound)
        else:
            recipient = find_object(self.iter_transfer_recipients(account.id), id=transfer.recipient_id, error=RecipientNotFound)

        transfer.amount = transfer.amount.quantize(Decimal('.01'))

        return self.browser.init_transfer(account, recipient, transfer)

    def execute_transfer(self, transfer, **params):
        if self.config['website'].get() != 'par':
            raise NotImplementedError()
        return self.browser.execute_transfer(transfer)

    def transfer_check_exec_date(self, old_exec_date, new_exec_date):
        return old_exec_date <= new_exec_date <= old_exec_date + timedelta(days=2)
