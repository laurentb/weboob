# -*- coding: utf-8 -*-

# Copyright(C) 2014      Alexandre Morignot
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


from weboob.tools.backend import Module
from weboob.tools.value import Value, ValueBackendPassword
from weboob.tools.backend import BackendConfig
from weboob.capabilities.calendar import CapCalendarEvent, BaseCalendarEvent, CATEGORIES

from .browser import ResidentadvisorBrowser

from datetime import timedelta


__all__ = ['ResidentadvisorModule']


class ResidentadvisorModule(Module, CapCalendarEvent):
    NAME = 'residentadvisor'
    DESCRIPTION = u'residentadvisor website'
    MAINTAINER = u'Alexandre Morignot'
    EMAIL = 'erdnaxeli@cervoi.se'
    LICENSE = 'AGPLv3+'
    VERSION = '1.5'

    BROWSER = ResidentadvisorBrowser

    CONFIG = BackendConfig(Value('username', label='Username or email', default=''),
                           ValueBackendPassword('password', label='Password', default=''),
                           Value('country', required=True),
                           Value('city', required=True))

    ASSOCIATED_CATEGORIES = [CATEGORIES.CONCERT]

    _city_id = None

    @property
    def city_id(self):
        if not self._city_id:
            self._city_id = self.browser.get_country_city_id(
                    country = self.config['country'].get(),
                    city = self.config['city'].get())

        return self._city_id

    def create_default_browser(self):
        password = None
        username = self.config['username'].get()

        if len(username) > 0:
            password = self.config['password'].get()

        return self.create_browser(username, password)

    def attends_event(self, event, is_attending):
        """
        Attends or not to an event
        :param event : the event
        :type event : BaseCalendarEvent
        :param is_attending : is attending to the event or not
        :type is_attending : bool
        """
        self.browser.attends_event(event.id, is_attending)

    def get_event(self, _id):
        """
        Get an event from an ID.

        :param _id: id of the event
        :type _id: str
        :rtype: :class:`BaseCalendarEvent` or None is fot found.
        """
        return self.browser.get_event(_id)

    def list_events(self, date_from, date_to):
        """
        list coming event.

        :param date_from: date of beguinning of the events list
        :type date_from: date
        :param date_to: date of ending of the events list
        :type date_to: date
        :rtype: iter[:class:`BaseCalendarEvent`]
        """
        # we check if date_to is defined
        try:
            date_to.date()
        except:
            # default is week
            date_to = date_from + timedelta(days = 7)

        delta = date_to - date_from

        while delta.days >= 0 :
            v = 'week'

            if delta.days > 7:
                v = 'month'

            for event in self.browser.get_events(v = v, date = date_from, city = self.city_id):
                if event.start_date <= date_to:
                    yield event

            if v == 'week':
                date_from += timedelta(days = 7)
            else:
                date_from += timedelta(days = 30)

            delta = date_to - date_from

    def search_events(self, query):
        """
        Search event

        :param query: search query
        :type query: :class:`Query`
        :rtype: iter[:class:`BaseCalendarEvent`]
        """
        if not self.has_matching_categories(query):
            return

        events = None

        if query.city:
            # FIXME
            # we need the country to search the city_id in an efficient way
            city_id = self.browser.get_city_id(query.city)

            events = self.browser.get_events(city = city_id)
        elif query.summary:
            events = self.browser.search_events_by_summary(query.summary)
        else:
            events = self.list_events(query.start_date, query.end_date)

        for event in events:
            event = self.fillobj(event, ['ticket'])
            if event.ticket in query.ticket:
                yield event

    def fill_event(self, event, fields):
        if set(fields) & set(('end_date', 'price', 'description', 'ticket')):
            return self.get_event(event.id)

        return event

    OBJECTS = {BaseCalendarEvent: fill_event}
