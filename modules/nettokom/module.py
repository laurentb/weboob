# -*- coding: utf-8 -*-

# Copyright(C) 2012 Florent Fourcot
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


from weboob.capabilities.bill import CapDocument, Subscription, SubscriptionNotFound, Detail
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword

from .browser import Nettokom


__all__ = ['NettoKomModule']


class NettoKomModule(Module, CapDocument):
    NAME = 'nettokom'
    MAINTAINER = u'Florent Fourcot'
    EMAIL = 'weboob@flo.fourcot.fr'
    VERSION = '1.2'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = 'Nettokom website'
    CONFIG = BackendConfig(ValueBackendPassword('login',
                                                label='Account ID (phone number)',
                                                masked=False,
                                                regexp='^(\d{8,13}|)$'),
                           ValueBackendPassword('password',
                                                label='Password')
                          )
    BROWSER = Nettokom

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(),
                                   self.config['password'].get())

    def iter_subscription(self):
        for subscription in self.browser.get_subscription_list():
            yield subscription

    def get_subscription(self, _id):
        with self.browser:
            subscription = self.browser.get_subscription(_id)
        if subscription:
            return subscription
        else:
            raise SubscriptionNotFound()

    def iter_documents_history(self, subscription):
        with self.browser:
            for history in self.browser.get_history():
                yield history

    # The subscription is actually useless, but maybe for the futur...
    def get_details(self, subscription):
        with self.browser:
            for detail in self.browser.get_details():
                yield detail

    def get_balance(self, subscription):
        if not isinstance(subscription, Subscription):
            subscription = self.get_subscription(subscription)
        balance = Detail()
        balance.id = "%s-balance" % subscription.id
        balance.price = subscription._balance
        balance.label = u"Balance %s" % subscription.id
        balance.currency = u'EUR'
        return balance
