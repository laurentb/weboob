# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
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
from weboob.capabilities.calendar import CapCalendarEvent, CATEGORIES

from .browser import SenscritiqueBrowser
from .calendar import SensCritiquenCalendarEvent

__all__ = ['SenscritiqueModule']


class SenscritiqueModule(Module, CapCalendarEvent):
    NAME = 'senscritique'
    DESCRIPTION = u'senscritique website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    LICENSE = 'AGPLv3+'
    VERSION = '1.5'
    ASSOCIATED_CATEGORIES = [CATEGORIES.TELE]
    BROWSER = SenscritiqueBrowser

    def search_events(self, query):
        if self.has_matching_categories(query):
            return self.list_events(query.start_date,
                                    query.end_date)

    def list_events(self, date_from, date_to=None):
        items = []
        for item in self.browser.list_events(date_from, date_to):
            items.append(item)

        items.sort(key=lambda o: o.start_date)
        return items

    def get_event(self, _id, event=None):
        return self.browser.get_event(_id, event)

    def fill_obj(self, event, fields):
        return self.get_event(event.id, event)

    OBJECTS = {SensCritiquenCalendarEvent: fill_obj}
