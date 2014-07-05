# -*- coding: utf-8 -*-

# Copyright(C) 2013      Christophe Gouiran
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

from weboob.capabilities.bill import CapBill, SubscriptionNotFound, BillNotFound, Subscription, Bill
from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.tools.value import ValueBackendPassword
from .browser import EdfBrowser

__all__ = ['EdfBackend']


class EdfBackend(BaseBackend, CapBill):
    NAME = 'edf'
    DESCRIPTION = u'Edf website: French power provider'
    MAINTAINER = u'Christophe Gouiran'
    EMAIL = 'bechris13250@gmail.com'
    VERSION = '0.j'
    LICENSE = 'AGPLv3+'
    BROWSER = EdfBrowser
    CONFIG = BackendConfig(ValueBackendPassword('login',
                                                label='Identifiant',
                                                masked=False),
                           ValueBackendPassword('password',
                                                label='Password',
                                                masked=True)
                           )
    BROWSER = EdfBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(),
                                   self.config['password'].get())

    def iter_subscription(self):
        return self.browser.iter_subscription_list()

    def get_subscription(self, _id):
        with self.browser:
            subscription = self.browser.get_subscription(_id)
        if not subscription:
            raise SubscriptionNotFound()
        else:
            return subscription

    def iter_bills_history(self, subscription):
        if not isinstance(subscription, Subscription):
            subscription = self.get_subscription(subscription)
        with self.browser:
            return self.browser.iter_history(subscription)

    def get_details(self, subscription):
        if not isinstance(subscription, Subscription):
            subscription = self.get_subscription(subscription)
        with self.browser:
            return self.browser.iter_details(subscription)

    def iter_bills(self, subscription):
        if not isinstance(subscription, Subscription):
            subscription = self.get_subscription(subscription)
        with self.browser:
            return self.browser.iter_bills(subscription)

    def get_bill(self, id):
        with self.browser:
            bill = self.browser.get_bill(id)
        if not bill:
            raise BillNotFound()
        else:
            return bill

    def download_bill(self, bill):
        if not isinstance(bill, Bill):
            bill = self.get_bill(bill)
        with self.browser:
            return self.browser.readurl(bill._url)
