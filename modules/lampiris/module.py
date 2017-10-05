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


from weboob.tools.backend import BackendConfig, Module
from weboob.tools.value import Value, ValueBackendPassword
from weboob.capabilities.base import find_object
from weboob.capabilities.bill import Bill, CapDocument, DocumentNotFound, SubscriptionNotFound, Subscription

from .browser import LampirisBrowser


__all__ = ['LampirisModule']


class LampirisModule(Module, CapDocument):
    NAME = 'lampiris'
    DESCRIPTION = u'French electricity provider Lampiris.fr'
    MAINTAINER = u'Phyks (Lucas Verney)'
    EMAIL = 'phyks@phyks.me'
    LICENSE = 'AGPLv3+'
    VERSION = '1.4'

    CONFIG = BackendConfig(
        Value(
            'email',
            label='Email',
        ),
        ValueBackendPassword(
            'password',
            label='Password'
        )
    )

    BROWSER = LampirisBrowser

    def create_default_browser(self):
        return self.create_browser(
            self.config['email'].get(),
            self.config['password'].get()
        )

    def download_document(self, id):
        """
        Download a document.

        :param id: ID of document
        :rtype: str
        :raises: :class:`DocumentNotFound`
        """
        if not isinstance(id, Bill):
            doc = self.get_document(id)
        else:
            doc = id
        if not doc.url:
            return None

        return self.browser.open(doc.url).content

    def get_document(self, id):
        """
        Get a document.

        :param id: ID of document
        :rtype: :class:`Document`
        :raises: :class:`DocumentNotFound`
        """
        return find_object(self.iter_documents(id.split("#")[0]),
                           id=id,
                           error=DocumentNotFound)

    def iter_documents(self, subscription):
        """
        Iter documents.

        :param subscription: subscription to get documents
        :type subscription: :class:`Subscription`
        :rtype: iter[:class:`Document`]
        """
        if not isinstance(subscription, Subscription):
            subscription = find_object(self.iter_subscription(),
                                       id=subscription,
                                       error=SubscriptionNotFound)

        return self.browser.get_documents(subscription)

    def iter_subscription(self):
        """
        Iter subscriptions.

        :rtype: iter[:class:`Subscription`]
        """
        return self.browser.get_subscriptions()
