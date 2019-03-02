# -*- coding: utf-8 -*-

# Copyright(C) 2017      Phyks (Lucas Verney)
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


from weboob.tools.backend import Module, BackendConfig
from weboob.capabilities.base import find_object
from weboob.capabilities.bill import (CapDocument, Bill, DocumentNotFound,
                                      Subscription)
from weboob.tools.value import Value, ValueBackendPassword

from .browser import MyFonciaBrowser


__all__ = ['MyFonciaModule']


class MyFonciaModule(Module, CapDocument):
    NAME = 'myfoncia'
    DESCRIPTION = u'Foncia billing capabilities'
    MAINTAINER = u'Phyks (Lucas Verney)'
    EMAIL = 'phyks@phyks.me'
    LICENSE = 'LGPLv3+'
    VERSION = '1.6'
    CONFIG = BackendConfig(
        Value(
            'login',
            label='Email address or Foncia ID'
        ),
        ValueBackendPassword(
            'password',
            label='Password'
        )
    )
    BROWSER = MyFonciaBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(),
                                   self.config['password'].get())

    def iter_subscription(self):
        return self.browser.get_subscriptions()

    def iter_documents(self, subscription):
        if isinstance(subscription, Subscription):
            subscription_id = subscription.id
        else:
            subscription_id = subscription
        return self.browser.get_documents(subscription_id)

    def get_document(self, bill):
        return find_object(
            self.iter_documents(bill.split("#")[0]),
            id=bill,
            error=DocumentNotFound
        )

    def download_document(self, bill):
        if not isinstance(bill, Bill):
            bill = self.get_document(bill)

        if not bill.url:
            return None

        return self.browser.open(bill.url).content
