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

from weboob.tools.backend import Module, BackendConfig
from weboob.tools.ordereddict import OrderedDict
from weboob.tools.value import Value, ValueBool
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
    VERSION = '1.1'
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

    CONFIG = BackendConfig(Value('tv_settings', label=u'T.V. package', choices=tv_settings_choices),
                           ValueBool('general', label='General', default=True),
                           ValueBool('cinema', label='Cinema', default=False),
                           )

    def get_package_and_channels(self):
        package = int(self.config['tv_settings'].get())
        channels = self.browser.get_selected_channels(package, self.config['general'].get(),
                                                      self.config['cinema'].get())
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

        items.sort(key=lambda o: o.start_date)
        return items

    def get_event(self, _id, event=None):
        package, channels = self.get_package_and_channels()
        return self.browser.get_event(_id, event, package=package, channels=channels)

    def fill_obj(self, event, fields):
        return self.get_event(event.id, event)

    OBJECTS = {SensCritiquenCalendarEvent: fill_obj}
