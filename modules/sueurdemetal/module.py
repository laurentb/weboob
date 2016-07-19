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
import datetime

from .browser import SueurDeMetalBrowser


__all__ = ['SueurDeMetalModule']


class Concert(BaseCalendarEvent):
    @classmethod
    def id2url(cls, _id):
        return 'http://www.sueurdemetal.com/detail-concert-metal.php?c=%s' % _id


class SueurDeMetalModule(Module, CapCalendarEvent):
    NAME = 'sueurdemetal'
    DESCRIPTION = u'SueurDeMetal French concerts list website'
    MAINTAINER = u'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '1.2'

    BROWSER = SueurDeMetalBrowser

    ASSOCIATED_CATEGORIES = [CATEGORIES.CONCERT]

    def __init__(self, *a, **kw):
        super(SueurDeMetalModule, self).__init__(*a, **kw)
        self.cities = {}

    def list_events(self, from_date, to_date=None):
        for d in self.browser.get_concerts_date(from_date, date_end=to_date):
            yield self._make_event(d)

    def search_events(self, query):
        if not self.has_matching_categories(query):
            return

        if query.city:
            city_id = self.find_city_id(query.city)
            for d in self.browser.get_concerts_city(city_id):
                if self._date_matches(d['date'], query):
                    yield self._make_event(d)
        else:
            for e in self.list_events(query.start_date, query.end_date):
                yield e

    def get_event(self, _id):
        d = self.browser.get_concert(_id)
        return self._make_event(d)

    def _make_event(self, d):
        event = Concert(d['id'])
        event.category = CATEGORIES.CONCERT
        event.start_date = d['date']
        event.end_date = datetime.datetime.combine(event.start_date.date(), datetime.time.max)
        event.summary = d['summary']
        event.url = d['url']

        if 'price' in d:
            event.price = d['price']

        if d['active']:
            event.status = STATUS.CONFIRMED
        else:
            event.status = STATUS.CANCELLED

        if 'city' in d:
            event.city = d['city']
        else:
            event.city = self.find_city_name(d['city_id'])
        event.transp = TRANSP.OPAQUE

        # "room, address" or "room" or "address" or ""
        location = ', '.join(filter(None, (d.get('room', ''), d.get('address', ''))))
        if location:
            event.location = location

        return event

    def _fetch_cities(self):
        if self.cities:
            return
        self.cities = self.browser.get_cities()

    def find_city_id(self, name):
        self._fetch_cities()
        name = name.lower()
        for c in self.cities:
            if c.lower() == name:
                return self.cities[c]['id']

    def find_city_name(self, _id):
        self._fetch_cities()
        for c in self.cities.values():
            if c['id'] == _id:
                return c['name']

    def _date_matches(self, date, query):
        return ((not query.start_date or query.start_date <= date) and
                (not query.end_date or date <= query.end_date))

    def fill_concert(self, obj, fields):
        if set(fields) & set(('price', 'location', 'description')):
            new_obj = self.get_event(obj.id)
            for field in fields:
                setattr(obj, field, getattr(new_obj, field))
        return obj

    OBJECTS = {Concert: fill_concert}
