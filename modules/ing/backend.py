# -*- coding: utf-8 -*-

# Copyright(C) 2010-2014 Romain Bignon, Florent Fourcot
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
from weboob.capabilities.base import UserError, find_object
from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.tools.value import ValueBackendPassword

from .browser import IngBrowser

__all__ = ['INGBackend']


class INGBackend(BaseBackend, ICapBank, ICapBill):
    NAME = 'ing'
    MAINTAINER = u'Florent Fourcot'
    EMAIL = 'weboob@flo.fourcot.fr'
    VERSION = '0.j'
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
    BROWSER = IngBrowser

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
        return self.browser.get_accounts_list()

    def get_account(self, _id):
        return find_object(self.browser.get_accounts_list(), id=_id, error=AccountNotFound)

    def iter_history(self, account):
        if not isinstance(account, Account):
            account = self.get_account(account)
        return self.browser.get_history(account)

    def iter_transfer_recipients(self, account):
        if not isinstance(account, Account):
            account = self.get_account(account)
        return self.browser.get_recipients(account)

    def transfer(self, account, recipient, amount, reason):
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
        if not isinstance(account, Account):
            account = self.get_account(account)
        return self.browser.get_investments(account)

    def iter_subscription(self):
        return self.browser.get_subscriptions()

    def get_subscription(self, _id):
        return find_object(self.browser.get_subscriptions(), id=_id, error=SubscriptionNotFound)

    def get_bill(self, _id):
        subscription = self.get_subscription(_id.split('-')[0])
        return find_object(self.browser.get_bills(subscription), id=_id, error=BillNotFound)

    def iter_bills(self, subscription):
        if not isinstance(subscription, Subscription):
            subscription = self.get_subscription(subscription)
        return self.browser.get_bills(subscription)

    def download_bill(self, bill):
        if not isinstance(bill, Bill):
            bill = self.get_bill(bill)
        self.browser.predownload(bill)
        request = self.browser.open("https://secure.ingdirect.fr" + bill._url, stream=True)
        assert(request.headers['content-type'] == "application/pdf")
        return request.content
