# -*- coding: utf-8 -*-

# Copyright(C) 2012-2014 Florent Fourcot
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

from weboob.capabilities.bill import CapBill, Subscription, Bill, SubscriptionNotFound, BillNotFound
from weboob.capabilities.base import find_object
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword

from .browser import Freemobile


__all__ = ['FreeMobileModule']


class FreeMobileModule(Module, CapBill):
    NAME = 'freemobile'
    MAINTAINER = u'Florent Fourcot'
    EMAIL = 'weboob@flo.fourcot.fr'
    VERSION = '1.1'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = 'Free Mobile website'
    CONFIG = BackendConfig(ValueBackendPassword('login',
                                                label='Account ID',
                                                masked=False,
                                                regexp='^(\d{8}|)$'),
                           ValueBackendPassword('password',
                                                label='Password')
                           )
    BROWSER = Freemobile

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(),
                                   self.config['password'].get())

    def iter_subscription(self):
        return self.browser.get_subscription_list()

    def get_subscription(self, _id):
        return find_object(self.iter_subscription(), id=_id, error=SubscriptionNotFound)

    def iter_bills_history(self, subscription):
        if not isinstance(subscription, Subscription):
            subscription = self.get_subscription(subscription)
        return self.browser.get_history(subscription)

    def get_bill(self, _id):
        subid = _id.split('.')[0]
        subscription = self.get_subscription(subid)

        return find_object(self.iter_bills(subscription), id=_id, error=BillNotFound)

    def iter_bills(self, subscription):
        if not isinstance(subscription, Subscription):
            subscription = self.get_subscription(subscription)
        return self.browser.iter_bills(subscription)

    def get_details(self, subscription):
        if not isinstance(subscription, Subscription):
            subscription = self.get_subscription(subscription)
        return self.browser.get_details(subscription)

    def download_bill(self, bill):
        if not isinstance(bill, Bill):
            bill = self.get_bill(bill)
        return self.browser.open(bill._url).content
