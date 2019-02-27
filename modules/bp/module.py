# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Nicolas Duhamel
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from decimal import Decimal
from weboob.capabilities.bank import CapBankWealth, CapBankTransferAddRecipient, Account, AccountNotFound, RecipientNotFound, TransferError
from weboob.capabilities.contact import CapContact
from weboob.capabilities.base import find_object, strict_find_object, NotAvailable
from weboob.capabilities.profile import CapProfile
from weboob.capabilities.bill import (
    CapDocument, Subscription, SubscriptionNotFound,
    Document, DocumentNotFound,
)
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword, Value

from .browser import BPBrowser, BProBrowser


__all__ = ['BPModule']


class BPModule(
    Module, CapBankWealth, CapBankTransferAddRecipient,
    CapContact, CapProfile, CapDocument,
):

    NAME = 'bp'
    MAINTAINER = u'Nicolas Duhamel'
    EMAIL = 'nicolas@jombi.fr'
    VERSION = '1.6'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u'La Banque Postale'
    CONFIG = BackendConfig(ValueBackendPassword('login',    label='Identifiant', masked=False),
                           ValueBackendPassword('password', label='Mot de passe', regexp='^(\d{6})$'),
                           Value('website', label='Type de compte', default='par',
                                 choices={'par': 'Particuliers', 'pro': 'Professionnels'}))

    def create_default_browser(self):
        b = {'par': BPBrowser, 'pro': BProBrowser}

        self.BROWSER = b[self.config['website'].get()]

        return self.create_browser(self.config['login'].get(), self.config['password'].get(), weboob=self.weboob)

    def iter_accounts(self):
        return self.browser.get_accounts_list()

    def get_account(self, _id):
        return find_object(self.browser.get_accounts_list(), id=_id, error=AccountNotFound)

    def iter_history(self, account):
        return self.browser.get_history(account)

    def iter_coming(self, account):
        return self.browser.get_coming(account)

    def iter_investment(self, account):
        return self.browser.iter_investment(account)

    def iter_transfer_recipients(self, origin_account):
        if self.config['website'].get() != 'par':
            raise NotImplementedError()
        if isinstance(origin_account, Account):
            origin_account = origin_account.id
        return self.browser.iter_recipients(origin_account)

    def init_transfer(self, transfer, **params):
        if self.config['website'].get() != 'par':
            raise NotImplementedError()

        self.logger.info('Going to do a new transfer')
        account = strict_find_object(self.iter_accounts(), iban=transfer.account_iban)
        if not account:
            account = strict_find_object(self.iter_accounts(), id=transfer.account_id, error=AccountNotFound)

        recipient = strict_find_object(self.iter_transfer_recipients(account.id), iban=transfer.recipient_iban)
        if not recipient:
            recipient = strict_find_object(self.iter_transfer_recipients(account.id), id=transfer.recipient_id, error=RecipientNotFound)

        try:
            # quantize to show 2 decimals.
            amount = Decimal(transfer.amount).quantize(Decimal(10) ** -2)
        except (AssertionError, ValueError):
            raise TransferError('something went wrong')

        # format label like label sent by firefox or chromium browser
        transfer.label = transfer.label.encode('latin-1', errors="xmlcharrefreplace").decode('latin-1')

        return self.browser.init_transfer(account, recipient, amount, transfer)

    def transfer_check_label(self, old, new):
        old = old.encode('latin-1', errors="xmlcharrefreplace").decode('latin-1')
        return super(BPModule, self).transfer_check_label(old, new)

    def execute_transfer(self, transfer, **params):
        return self.browser.execute_transfer(transfer)

    def new_recipient(self, recipient, **kwargs):
        return self.browser.new_recipient(recipient, **kwargs)

    def iter_contacts(self):
        if self.config['website'].get() != 'par':
            raise NotImplementedError()

        return self.browser.get_advisor()

    def get_profile(self):
        return self.browser.get_profile()

    def get_document(self, _id):
        subscription_id = _id.split('_')[0]
        subscription = self.get_subscription(subscription_id)
        return find_object(self.iter_documents(subscription), id=_id, error=DocumentNotFound)

    def get_subscription(self, _id):
        return find_object(self.iter_subscription(), id=_id, error=SubscriptionNotFound)

    def iter_documents(self, subscription):
        if not isinstance(subscription, Subscription):
            subscription = self.get_subscription(subscription)

        return self.browser.iter_documents(subscription)

    def iter_subscription(self):
        return self.browser.iter_subscriptions()

    def download_document(self, document):
        if not isinstance(document, Document):
            document = self.get_document(document)
        if document.url is NotAvailable:
            return

        return self.browser.download_document(document)

    def iter_resources(self, objs, split_path):
        if Account in objs:
            self._restrict_level(split_path)
            return self.iter_accounts()
        if Subscription in objs:
            self._restrict_level(split_path)
            return self.iter_subscription()
