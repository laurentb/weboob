# -*- coding: utf-8 -*-

# Copyright(C) 2013 Romain Bignon
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


from weboob.capabilities.bank import CapBankWealth, CapBankTransfer, AccountNotFound, RecipientNotFound
from weboob.capabilities.base import find_object, NotAvailable
from weboob.capabilities.bank import Account, TransferInvalidLabel
from weboob.capabilities.bill import CapDocument, Subscription, Document, DocumentNotFound, SubscriptionNotFound
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword

from .browser import AXABanque, AXAAssurance


__all__ = ['AXABanqueModule']


class AXABanqueModule(Module, CapBankWealth, CapBankTransfer, CapDocument):
    NAME = 'axabanque'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.4'
    DESCRIPTION = u'AXA Banque'
    LICENSE = 'AGPLv3+'
    CONFIG = BackendConfig(ValueBackendPassword('login',    label='Identifiant', masked=False),
                           ValueBackendPassword('password', label='Code', regexp='\d+'))
    BROWSER = AXABanque

    def create_default_browser(self):
        login = self.config['login'].get()
        self.BROWSER = AXABanque if login.isdigit() else AXAAssurance
        return self.create_browser(login, self.config['password'].get(),
                                   weboob=self.weboob)

    def get_account(self, _id):
        return find_object(self.browser.iter_accounts(), id=_id, error=AccountNotFound)

    def iter_accounts(self):
        return self.browser.iter_accounts()

    def iter_investment(self, account):
        return self.browser.iter_investment(account)

    def iter_history(self, account):
        return self.browser.iter_history(account)

    def iter_coming(self, account):
        return self.browser.iter_coming(account)

    def iter_transfer_recipients(self, origin_account):
        if isinstance(origin_account, Account):
            origin_account = origin_account.id
        # Only 11 first character are required to iter recipient
        origin_account = origin_account[:11]
        return self.browser.iter_recipients(origin_account)

    def init_transfer(self, transfer, **params):
        if not transfer.label:
            raise TransferInvalidLabel()

        self.logger.info('Going to do a new transfer')
        if transfer.account_iban:
            account = find_object(self.iter_accounts(), iban=transfer.account_iban, error=AccountNotFound)
        else:
            account = find_object(self.iter_accounts(), id=transfer.account_id, error=AccountNotFound)

        if transfer.recipient_iban:
            recipient = find_object(self.iter_transfer_recipients(account.id), iban=transfer.recipient_iban, error=RecipientNotFound)
        else:
            recipient = find_object(self.iter_transfer_recipients(account.id), id=transfer.recipient_id, error=RecipientNotFound)

        assert account.id.isdigit()
        # Only 11 first character are required to do transfer
        account.id = account.id[:11]

        return self.browser.init_transfer(account, recipient, transfer.amount, transfer.label)

    def execute_transfer(self, transfer, **params):
        return self.browser.execute_transfer(transfer)

    def transfer_check_label(self, old, new):
        old = old.upper()
        return super(AXABanqueModule, self).transfer_check_label(old, new)

    def transfer_check_account_id(self, old, new):
        old = old[:11]
        return super(AXABanqueModule, self).transfer_check_label(old, new)

    def iter_subscription(self):
        return self.browser.get_subscription_list()

    def get_subscription(self, _id):
        return find_object(self.iter_subscription(), id=_id, error=SubscriptionNotFound)

    def get_document(self, _id):
        subid = _id.rsplit('_', 1)[0]
        subscription = self.get_subscription(subid)

        return find_object(self.iter_documents(subscription), id=_id, error=DocumentNotFound)

    def iter_documents(self, subscription):
        if not isinstance(subscription, Subscription):
            subscription = self.get_subscription(subscription)
        return self.browser.iter_documents(subscription)

    def download_document(self, document):
        if not isinstance(document, Document):
            document = self.get_document(document)
        if document.url is NotAvailable:
            return
        return self.browser.download_document(document.url)

    def iter_resources(self, objs, split_path):
        if Account in objs:
            self._restrict_level(split_path)
            return self.iter_accounts()
        if Subscription in objs:
            self._restrict_level(split_path)
            return self.iter_subscription()
