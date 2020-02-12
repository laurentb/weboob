# -*- coding: utf-8 -*-

# Copyright(C) 2012 Gilles-Alexandre Quenot
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


from weboob.capabilities.base import find_object
from weboob.capabilities.bank import (
    CapBankWealth, CapBankTransferAddRecipient, AccountNotFound, RecipientNotFound,
    TransferInvalidLabel, Account,
)
from weboob.capabilities.profile import CapProfile
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword, ValueTransient

from .browser import Fortuneo


__all__ = ['FortuneoModule']


class FortuneoModule(Module, CapBankWealth, CapBankTransferAddRecipient, CapProfile):
    NAME = 'fortuneo'
    MAINTAINER = u'Gilles-Alexandre Quenot'
    EMAIL = 'gilles.quenot@gmail.com'
    VERSION = '2.1'
    LICENSE = 'LGPLv3+'
    DESCRIPTION = u'Fortuneo'
    CONFIG = BackendConfig(
        ValueBackendPassword('login', label='Identifiant', masked=False, required=True),
        ValueBackendPassword('password', label='Mot de passe', required=True),
        ValueTransient('code'),
        ValueTransient('request_information')
    )
    BROWSER = Fortuneo

    def create_default_browser(self):
        return self.create_browser(
            self.config,
            self.config['login'].get(),
            self.config['password'].get(),
            weboob=self.weboob
        )

    def iter_accounts(self):
        """Iter accounts"""
        return self.browser.get_accounts_list()

    def get_account(self, _id):
        return find_object(self.iter_accounts(), id=_id, error=AccountNotFound)

    def iter_history(self, account):
        """Iter history of transactions on a specific account"""
        return self.browser.get_history(account)

    def iter_coming(self, account):
        return self.browser.get_coming(account)

    def iter_investment(self, account):
        return self.browser.get_investments(account)

    def get_profile(self):
        return self.browser.get_profile()

    def iter_transfer_recipients(self, origin_account):
        if isinstance(origin_account, Account):
            origin_account = origin_account.id
        return self.browser.iter_recipients(self.get_account(origin_account))

    def new_recipient(self, recipient, **params):
        recipient.label = recipient.label[:35].upper()
        return self.browser.new_recipient(recipient, **params)

    def init_transfer(self, transfer, **params):
        if not transfer.label:
            raise TransferInvalidLabel()

        self.logger.info('Going to do a new transfer')
        account = find_object(self.iter_accounts(), id=transfer.account_id, error=AccountNotFound)

        if transfer.recipient_iban:
            recipient = find_object(self.iter_transfer_recipients(account.id), iban=transfer.recipient_iban, error=RecipientNotFound)
        else:
            recipient = find_object(self.iter_transfer_recipients(account.id), id=transfer.recipient_id, error=RecipientNotFound)

        return self.browser.init_transfer(account, recipient, transfer.amount, transfer.label, transfer.exec_date)

    def execute_transfer(self, transfer, **params):
        return self.browser.execute_transfer(transfer)

# vim:ts=4:sw=4
