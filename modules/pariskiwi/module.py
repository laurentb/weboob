# -*- coding: utf-8 -*-

# Copyright(C) 2013      Vincent A
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


from weboob.tools.backend import Module
from weboob.capabilities.calendar import CapCalendarEvent, BaseCalendarEvent, CATEGORIES, TRANSP, STATUS
from datetime import datetime, time

from .browser import ParisKiwiBrowser


__all__ = ['ParisKiwiModule']


class ParisKiwiModule(Module, CapCalendarEvent):
    NAME = 'pariskiwi'
    DESCRIPTION = u'ParisKiwi website'
    MAINTAINER = u'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '1.4'

    BROWSER = ParisKiwiBrowser

    ASSOCIATED_CATEGORIES = [CATEGORIES.CONCERT]

    def search_events(self, query):
        if self.has_matching_categories(query):
            for event in self.list_events(query.start_date, query.end_date or None):
                yield event

    def list_events(self, date_from, date_to=None):
        for d in self.browser.list_events_all():
            if date_from and d['date'] < date_from:
                continue
            if date_to and d['date'] > date_to:
                break

            event = self.get_event(d['id'])
            if event:
                yield event

    def get_event(self, _id):
        d = self.browser.get_event(_id)
        if not d:
            return None
        return self._make_event(d)

    def _make_event(self, d):
        event = BaseCalendarEvent(d['id'])
        event.city = u'Paris'
        event.url = d['url']
        event.start_date = d['datetime']
        event.end_date = datetime.combine(d['datetime'].date(), time.max)
        event.summary = d['summary']
        event.category = CATEGORIES.CONCERT
        event.description = d['description']
        event.status = STATUS.CONFIRMED
        event.transp = TRANSP.OPAQUE
        if 'price' in d:
            event.price = d['price']
        if 'address' in d:
            event.location = d['address']
        return event

    def _make_false_event(self):
        event = BaseCalendarEvent('0')
        event.start_date = event.end_date = datetime.utcfromtimestamp(0)
        event.summary = u'NON EXISTING EVENT'
        event.status = STATUS.CANCELLED
        event.category = CATEGORIES.CONCERT
        event.transp = TRANSP.OPAQUE
        return event
