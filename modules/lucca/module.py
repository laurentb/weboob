# -*- coding: utf-8 -*-

# Copyright(C) 2018      Vincent A
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals


from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value, ValueBackendPassword
from weboob.capabilities.base import find_object
from weboob.capabilities.calendar import CapCalendarEvent
from weboob.capabilities.bill import (
    CapDocument, DocumentTypes, SubscriptionNotFound, DocumentNotFound,
    Subscription,
)

from .browser import LuccaBrowser


__all__ = ['LuccaModule']


class LuccaModule(Module, CapDocument, CapCalendarEvent):
    NAME = 'lucca'
    DESCRIPTION = 'Lucca RH'
    MAINTAINER = 'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '1.6'

    BROWSER = LuccaBrowser

    CONFIG = BackendConfig(
        Value('subdomain', label='Sub-domain', regexp=r'[\w-]+'),
        Value('login', label='Identifiant'),
        ValueBackendPassword('password', label='Mot de passe'),
    )

    accepted_document_types = (DocumentTypes.BILL,)

    def create_default_browser(self):
        return self.create_browser(
            self.config['subdomain'].get(),
            self.config['login'].get(),
            self.config['password'].get()
        )

    def get_event(self, _id):
        """
        Get an event from an ID.

        :param _id: id of the event
        :type _id: str
        :rtype: :class:`BaseCalendarEvent` or None is fot found.
        """
        raise NotImplementedError()

    def list_events(self, date_from, date_to=None):
        return self.browser.all_events(date_from, date_to)

    def search_events(self, query):
        for ev in self.browser.all_events(query.start_date, query.end_date):
            if query.summary:
                if query.summary.lower() not in ev.summary.lower():
                    continue
            yield ev

    # TODO merge contiguous events?

    def iter_subscription(self):
        return [self.browser.get_subscription()]

    def get_subscription(self, id):
        return find_object(self.iter_subscription(), id=id, error=SubscriptionNotFound)

    def iter_documents(self, subscription):
        if not isinstance(subscription, str):
            subscription = subscription.id
        return self.browser.iter_documents(subscription)

    def get_document(self, id):
        subid = id.split('_')[0]
        return find_object(self.iter_documents(subid), id=id, error=DocumentNotFound)

    def download_document(self, document):
        return self.browser.open(document.url).content

    def iter_resources(self, objs, split_path):
        if Subscription in objs:
            return CapDocument.iter_resources(self, objs, split_path)
        return CapCalendarEvent.iter_resources(self, objs, split_path)

