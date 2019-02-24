# -*- coding: utf-8 -*-

# Copyright(C) 2013      Bezleputh
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
from weboob.capabilities.calendar import CapCalendarEvent, CATEGORIES
import itertools

from .browser import BiplanBrowser
from.calendar import BiplanCalendarEvent

__all__ = ['BiplanModule']


class BiplanModule(Module, CapCalendarEvent):
    NAME = 'biplan'
    DESCRIPTION = u'lebiplan.org website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    LICENSE = 'AGPLv3+'
    VERSION = '1.5'
    ASSOCIATED_CATEGORIES = [CATEGORIES.CONCERT, CATEGORIES.THEATRE]
    BROWSER = BiplanBrowser

    def search_events(self, query):
        if self.has_matching_categories(query):
            theatre_events = []
            concert_events = []
            if CATEGORIES.CONCERT in query.categories:
                concert_events = self.browser.list_events_concert(query.start_date,
                                                                  query.end_date,
                                                                  query.city,
                                                                  query.categories)
            if CATEGORIES.THEATRE in query.categories:
                theatre_events = self.browser.list_events_theatre(query.start_date,
                                                                  query.end_date,
                                                                  query.city,
                                                                  query.categories)

            items = list(itertools.chain(concert_events, theatre_events))
            items.sort(key=lambda o: o.start_date)
            return items

    def list_events(self, date_from, date_to=None):
        items = list(itertools.chain(self.browser.list_events_concert(date_from, date_to),
                                     self.browser.list_events_theatre(date_from, date_to)))
        items.sort(key=lambda o: o.start_date)
        return items

    def get_event(self, _id):
        return self.browser.get_event(_id)

    def fill_obj(self, event, fields):
        return self.browser.get_event(event.id, event)

    OBJECTS = {BiplanCalendarEvent: fill_obj}
