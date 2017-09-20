# -*- coding: utf-8 -*-

# Copyright(C) 2017      Phyks (Lucas Verney)
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

from __future__ import unicode_literals


from weboob.tools.backend import Module, BackendConfig
from weboob.capabilities.bill import CapDocument, Bill, DocumentNotFound
from weboob.tools.value import Value, ValueBackendPassword

from .browser import MyFonciaBrowser


__all__ = ['MyFonciaModule']


class MyFonciaModule(Module, CapDocument):
    NAME = 'myfoncia'
    DESCRIPTION = u'Foncia billing capabilities'
    MAINTAINER = u'Phyks (Lucas Verney)'
    EMAIL = 'phyks@phyks.me'
    LICENSE = 'AGPLv3+'
    VERSION = '1.4'
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
        return self.browser.get_documents(subscription)

    def get_document(self, bill):
        try:
            return next(
                document
                for document in self.iter_documents(bill.split("#")[0])
                if document.id == bill
            )
        except StopIteration:
            raise DocumentNotFound

    def download_document(self, bill):
        if not isinstance(bill, Bill):
            bill = self.get_document(bill)

        if not bill.url:
            return None

        return self.browser.open(bill.url).content
