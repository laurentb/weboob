# -*- coding: utf-8 -*-

# Copyright(C) 2010-2013 Romain Bignon, Florent Fourcot
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


from weboob.capabilities.bank import ICapBank, AccountNotFound,\
        Account, Recipient
from weboob.capabilities.bill import ICapBill, Bill, Subscription,\
        SubscriptionNotFound, BillNotFound
from weboob.capabilities.base import UserError
from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.tools.value import ValueBackendPassword

from .browser import Ing

__all__ = ['INGBackend']


class INGBackend(BaseBackend, ICapBank, ICapBill):
    NAME = 'ing'
    MAINTAINER = u'Florent Fourcot'
    EMAIL = 'weboob@flo.fourcot.fr'
    VERSION = '0.i'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = 'ING Direct'
    CONFIG = BackendConfig(ValueBackendPassword('login',
                                                label=u'Numéro client',
                                                masked=False),
                           ValueBackendPassword('password',
                                                label='Code secret',
                                                regexp='^(\d{6}|)$'),
                           ValueBackendPassword('birthday',
                                                label='Date de naissance',
                                                regexp='^(\d{8}|)$',
                                                masked=False)
                          )
    BROWSER = Ing

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

    def iter_history(self, account):
        with self.browser:
            for history in self.browser.get_history(account.id):
                yield history

    def iter_transfer_recipients(self, account):
        with self.browser:
            if not isinstance(account, Account):
                account = self.get_account(account)
            for recipient in self.browser.get_recipients(account):
                yield recipient

    def transfer(self, account, recipient, amount, reason):
        with self.browser:
            if not reason:
                raise UserError('Reason is mandatory to do a transfer on ING website')
            if not isinstance(account, Account):
                account = self.get_account(account)
            if not isinstance(recipient, Recipient):
                # Remove weboob identifier prefix (LA-, CC-...)
                if "-" in recipient:
                    recipient = recipient.split('-')[1]
            return self.browser.transfer(account, recipient, amount, reason)

    def iter_investment(self, account):
        with self.browser:
            if not isinstance(account, Account):
                account = self.get_account(account)
            for investment in self.browser.get_investments(account):
                yield investment

    def iter_subscription(self):
        for subscription in self.browser.get_subscriptions():
            yield subscription

    def get_subscription(self, _id):
        for subscription in self.browser.get_subscriptions():
            if subscription.id == _id:
                return subscription
        raise SubscriptionNotFound()

    def get_bill(self, id):
        subscription = self.get_subscription(id.split('-')[0])
        for bill in self.browser.get_bills(subscription):
            if bill.id == id:
                return bill
        raise BillNotFound()

    def iter_bills(self, subscription):
        if not isinstance(subscription, Subscription):
            subscription = self.get_subscription(subscription)
        return self.browser.get_bills(subscription)

    def download_bill(self, bill):
        if not isinstance(bill, Bill):
            bill = self.get_bill(bill)
        self.browser.predownload(bill)
        with self.browser:
            return self.browser.readurl("https://secure.ingdirect.fr" + bill._url)
