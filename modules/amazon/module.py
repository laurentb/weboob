# -*- coding: utf-8 -*-

# Copyright(C) 2014      Oleg Plakhotniuk
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


from weboob.capabilities.bill import CapDocument, Subscription, Bill, SubscriptionNotFound, DocumentNotFound
from weboob.capabilities.shop import CapShop, Order
from weboob.capabilities.base import find_object
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value, ValueBackendPassword
from weboob.tools.ordereddict import OrderedDict

from .browser import Amazon
from .fr.browser import AmazonFR

__all__ = ['AmazonModule']


class AmazonModule(Module, CapShop, CapDocument):
    NAME = 'amazon'
    MAINTAINER = u'Oleg Plakhotniuk'
    EMAIL = 'olegus8@gmail.com'
    VERSION = '1.2'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u'Amazon'

    website_choices = OrderedDict([(k, u'%s (%s)' % (v, k)) for k, v in sorted({
        'www.amazon.com': u'Amazon.com',
        'www.amazon.fr': u'Amazon France',
        }.iteritems())])

    BROWSERS = {
        'www.amazon.com': Amazon,
        'www.amazon.fr': AmazonFR,
        }

    CONFIG = BackendConfig(
        Value('website',  label=u'Website', choices=website_choices, default='www.amazon.com'),
        ValueBackendPassword('email', label='Username', masked=False),
        ValueBackendPassword('password', label='Password'))

    def create_default_browser(self):
        self.BROWSER = self.BROWSERS[self.config['website'].get()]
        return self.create_browser(self.config['email'].get(),
                                   self.config['password'].get())

    def get_currency(self):
        return self.browser.get_currency()

    def get_order(self, id_):
        return self.browser.get_order(id_)

    def iter_orders(self):
        return self.browser.iter_orders()

    def iter_payments(self, order):
        if not isinstance(order, Order):
            order = self.get_order(order)
        return self.browser.iter_payments(order)

    def iter_items(self, order):
        if not isinstance(order, Order):
            order = self.get_order(order)
        return self.browser.iter_items(order)

    def iter_resources(self, objs, split_path):
        if Order in objs:
            self._restrict_level(split_path)
            return self.iter_orders()
        if Subscription in objs:
            self._restrict_level(split_path)
            return self.iter_subscription()

    def iter_subscription(self):
        return self.browser.get_subscription_list()

    def get_subscription(self, _id):
        return find_object(self.iter_subscription(), id=_id, error=SubscriptionNotFound)

    def get_document(self, _id):
        subid = _id.split('.')[0]
        subscription = self.get_subscription(subid)
        return find_object(self.iter_documents(subscription), id=_id, error=DocumentNotFound)

    def iter_documents(self, subscription):
        if not isinstance(subscription, Subscription):
            subscription = self.get_subscription(subscription)
        return self.browser.iter_documents(subscription)

    def download_document(self, bill):
        if not isinstance(bill, Bill):
            bill = self.get_document(bill)
        if bill._url:
            return self.browser.open(bill._url).content
        return None
