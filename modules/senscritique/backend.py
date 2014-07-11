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

from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.tools.ordereddict import OrderedDict
from weboob.tools.value import Value, ValueBool
from weboob.capabilities.calendar import CapCalendarEvent, CATEGORIES

from .browser import SenscritiqueBrowser
from .calendar import SensCritiquenCalendarEvent

__all__ = ['SenscritiqueBackend']


class SenscritiqueBackend(BaseBackend, CapCalendarEvent):
    NAME = 'senscritique'
    DESCRIPTION = u'senscritique website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    LICENSE = 'AGPLv3+'
    VERSION = '0.j'
    ASSOCIATED_CATEGORIES = [CATEGORIES.TELE]
    BROWSER = SenscritiqueBrowser

    tv_settings_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '000000': u'-- Indifférent --',
        '9': u'TNT',
        '1': u'Canalsat',
        '2': u'Numericable',
        '10': u'Orange',
        '11': u'Free',
        '12': u'SFR',
        '15': u'Darty box via ADSL',
        '16': u'Bouygues',
    }.iteritems())])

    """
    dict that represents ids list of general-interest channels included in a tv package
    {'tv package id': ['general-interest channels ids list']}
    """
    general = {
        9: [46, 2, 48, 56],
        1: [49, 46, 21, 2, 36, 59, 54, 48, 56, 50, 32, 1, 51, 24, 38, 34, 37, 6, 25, 11, 53, 26, 47],
        2: [49, 46, 21, 2, 36, 59, 54, 48, 56, 50, 32, 1, 51, 24, 38, 34, 37, 6, 25, 11, 53, 26, 47],
        10: [46, 46, 2, 36, 59, 54, 32, 24, 34, 37, 53, 47],
        11: [46, 46, 2, 36, 59, 54, 32, 24, 34, 37, 53, 47],
        12: [49, 46, 2, 36, 59, 54, 32, 24, 34, 37, 53, 47],
        15: [49, 46, 2, 36, 32, 24, 34, 37, 53, 47],
        16: [49, 46, 2, 36, 59, 54, 32, 24, 34, 37, 53, 47],
    }

    """
    dict that represents ids list of cinema channels included in a tv package
    {'tv package id': ['cinema channels ids list']}
    """
    cinema = {
        9: [10, 7],
        1: [10, 7, 9, 8, 52, 19, 18, 17, 16, 20, 15, 14, 4055, 44, 3, 45, 42, 41, 43, 13, 12],
        2: [10, 7, 9, 8, 52, 19, 18, 17, 16, 20, 15, 14, 4055, 44, 3, 45, 42, 41, 43, 13, 12],
        10: [10, 7, 9, 8, 52, 19, 18, 17, 16, 20, 15, 14, 44, 3, 45, 42, 41, 43, 13, 12],
        11: [10, 7, 9, 8, 52, 19, 18, 17, 16, 20, 15, 14, 4055, 44, 3, 45, 42, 41, 43, 13, 12],
        12: [10, 7, 9, 8, 52, 19, 18, 17, 16, 20, 15, 14, 44, 3, 45, 42, 41, 43, 13, 12],
        15: [10, 7, 9, 8, 52, 19, 18, 17, 16, 20, 15, 14, 44, 3, 45, 42, 41, 43, 13, 12],
        16: [10, 7, 9, 8, 52, 19, 18, 17, 16, 20, 15, 14, 4055, 44, 3, 45, 42, 41, 43, 13, 12],
    }

    CONFIG = BackendConfig(Value('tv_settings', label=u'T.V. package', choices=tv_settings_choices),
                           ValueBool('general', label='General', default=True),
                           ValueBool('cinema', label='Cinema', default=False),
                           )

    def get_package_and_channels(self):
        package = int(self.config['tv_settings'].get())
        channels = []
        if package:
            if self.config['general'].get():
                channels += self.general[package]

            if self.config['cinema'].get():
                channels += self.cinema[package]

        return package, channels

    def search_events(self, query):
        if self.has_matching_categories(query):
            package, channels = self.get_package_and_channels()
            return self.browser.list_events(query.start_date,
                                            query.end_date,
                                            package,
                                            channels)

    def list_events(self, date_from, date_to=None):
        items = []
        package, channels = self.get_package_and_channels()
        for item in self.browser.list_events(date_from, date_to, package, channels):
            items.append(item)

        items.sort(key=lambda o:o.start_date)
        return items

    def get_event(self, _id, event=None):
        package, channels = self.get_package_and_channels()
        return self.browser.get_event(_id, event, package=package, channels=channels)

    def fill_obj(self, event, fields):
        return self.get_event(event.id, event)

    OBJECTS = {SensCritiquenCalendarEvent: fill_obj}
