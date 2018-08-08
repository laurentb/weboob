# -*- coding: utf-8 -*-

# Copyright(C) 2018      Vincent A
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
from weboob.tools.value import Value, ValueBackendPassword
from weboob.capabilities.calendar import CapCalendarEvent

from .browser import LuccaBrowser


__all__ = ['LuccaModule']


class LuccaModule(Module, CapCalendarEvent):
    NAME = 'figgo'
    DESCRIPTION = 'Figgo - Lucca congés et absences'
    MAINTAINER = 'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '1.4'

    BROWSER = LuccaBrowser

    CONFIG = BackendConfig(
        Value('subdomain', label='Sub-domain', regexp=r'[\w-]+'),
        Value('login', label='Identifiant'),
        ValueBackendPassword('password', label='Mot de passe'),
    )

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
