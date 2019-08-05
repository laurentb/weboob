# -*- coding: utf-8 -*-

# Copyright(C) 2010-2014 Romain Bignon, Florent Fourcot
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


from decimal import Decimal
from datetime import timedelta

from weboob.capabilities.bank import CapBankWealth, CapBankTransfer, Account, AccountNotFound, RecipientNotFound
from weboob.capabilities.bill import (
    CapDocument, Bill, Subscription,
    SubscriptionNotFound, DocumentNotFound, DocumentTypes,
)
from weboob.capabilities.profile import CapProfile
from weboob.capabilities.base import find_object, strict_find_object
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword, ValueDate

from .api_browser import IngAPIBrowser

__all__ = ['INGModule']


class INGModule(Module, CapBankWealth, CapBankTransfer, CapDocument, CapProfile):
    NAME = 'ing'
    MAINTAINER = 'Florent Fourcot'
    EMAIL = 'weboob@flo.fourcot.fr'
    VERSION = '1.6'
    LICENSE = 'LGPLv3+'
    DESCRIPTION = 'ING France'
    CONFIG = BackendConfig(ValueBackendPassword('login',
                                                label='Numéro client',
                                                masked=False,
                                                regexp='^(\d{1,10})$'),
                           ValueBackendPassword('password',
                                                label='Code secret',
                                                regexp='^(\d{6})$'),
                           ValueDate('birthday',
                                     label='Date de naissance',
                                     formats=('%d%m%Y', '%d/%m/%Y', '%d-%m-%Y'))
                           )
    BROWSER = IngAPIBrowser

    accepted_document_types = (DocumentTypes.STATEMENT,)

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(),
                                   self.config['password'].get(),
                                   birthday=self.config['birthday'].get())

    def iter_resources(self, objs, split_path):
        if Account in objs:
            self._restrict_level(split_path)
            return self.iter_accounts()
        if Subscription in objs:
            self._restrict_level(split_path)
            return self.iter_subscription()

    ############# CapBank #############
    def iter_accounts(self):
        return self.browser.iter_matching_accounts()

    def get_account(self, _id):
        return find_object(self.iter_accounts(), id=_id, error=AccountNotFound)

    def iter_history(self, account):
        if not isinstance(account, Account):
            account = self.get_account(account)
        return self.browser.iter_history(account)

    def iter_coming(self, account):
        if not isinstance(account, Account):
            account = self.get_account(account)
        return self.browser.iter_coming(account)

    ############# CapWealth #############
    def iter_investment(self, account):
        if not isinstance(account, Account):
            account = self.get_account(account)
        return self.browser.get_investments(account)

    ############# CapTransfer #############
    def iter_transfer_recipients(self, account):
        if not isinstance(account, Account):
            account = self.get_account(account)
        return self.browser.iter_recipients(account)

    def init_transfer(self, transfer, **params):
        self.logger.info('Going to do a new transfer')

        account = strict_find_object(self.iter_accounts(), id=transfer.account_id, error=AccountNotFound)

        recipient = strict_find_object(self.iter_transfer_recipients(account), id=transfer.recipient_id, error=RecipientNotFound)

        transfer.amount = Decimal(transfer.amount).quantize(Decimal('.01'))

        return self.browser.init_transfer(account, recipient, transfer)

    def execute_transfer(self, transfer, **params):
        return self.browser.execute_transfer(transfer)

    def transfer_check_exec_date(self, old_exec_date, new_exec_date):
        # week-end + 1 holiday
        return old_exec_date <= new_exec_date <= old_exec_date + timedelta(days=3)

    ############# CapDocument #############
    def iter_subscription(self):
        return self.browser.get_subscriptions()

    def get_subscription(self, _id):
        return find_object(self.browser.get_subscriptions(), id=_id, error=SubscriptionNotFound)

    def get_document(self, _id):
        subscription = self.get_subscription(_id.split('-')[0])
        return find_object(self.browser.get_documents(subscription), id=_id, error=DocumentNotFound)

    def iter_documents(self, subscription):
        if not isinstance(subscription, Subscription):
            subscription = self.get_subscription(subscription)
        return self.browser.get_documents(subscription)

    def download_document(self, bill):
        if not isinstance(bill, Bill):
            bill = self.get_document(bill)

        return self.browser.download_document(bill).content

    ############# CapProfile #############
    def get_profile(self):
        return self.browser.get_profile()
