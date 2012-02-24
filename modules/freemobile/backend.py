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


from weboob.capabilities.bill import ICapBill, SubscriptionNotFound
from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.tools.value import ValueBackendPassword

from .browser import Freemobile


__all__ = ['FreeMobileBackend']


class FreeMobileBackend(BaseBackend, ICapBill):
    NAME = 'freemobile'
    MAINTAINER = 'Florent Fourcot'
    EMAIL = 'weboob@flo.fourcot.fr'
    VERSION = '0.b'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = 'Free Mobile website'
    CONFIG = BackendConfig(ValueBackendPassword('login',      label='Account ID', masked=False, regexp='^(\d{8}|)$'),
                           ValueBackendPassword('password',   label='Password')
                          )
    BROWSER = Freemobile

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(),
                                   self.config['password'].get())

    def iter_subscription(self):
        for subscription in self.browser.get_subscription_list():
            yield subscription

    def get_subscription(self, _id):
        if not _id.isdigit():
            raise SubscriptionNotFound()
        with self.browser:
            subscription = self.browser.get_subscription(_id)
        if subscription:
            return subscription
        else:
            raise SubscriptionNotFound()

    
    def iter_history(self, subscription):
        raise NotImplementedError()
    
    def get_pdf(self, account):
        raise NotImplementedError()

    # The subscription is actually useless, but maybe for the futur...
    def get_details(self, subscription): 
        with self.browser:
            for detail in self.browser.get_details():
                yield detail

