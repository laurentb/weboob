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

from collections import OrderedDict

from weboob.tools.backend import Module, BackendConfig
from weboob.capabilities.calendar import CapCalendarEvent, CATEGORIES
from weboob.tools.value import Value

from .browser import RazibusBrowser
from .calendar import RazibusCalendarEvent

__all__ = ['RazibusModule']


class RazibusModule(Module, CapCalendarEvent):
    NAME = 'razibus'
    DESCRIPTION = u'site annonçant les évènements attendus par les punks a chiens'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    LICENSE = 'AGPLv3+'
    VERSION = '1.4'
    ASSOCIATED_CATEGORIES = [CATEGORIES.CONCERT]
    BROWSER = RazibusBrowser

    region_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '': u'-- Indifférent --',
        'Alsace': u'Alsace',
        'Aquitaine': u'Aquitaine',
        'Auvergne': u'Auvergne',
        'Basse-Normandie': u'Basse-Normandie',
        'Bourgogne': u'Bourgogne',
        'Bretagne': u'Bretagne',
        'Centre': u'Centre',
        'Champagne-Ardenne': u'Champagne-Ardenne',
        'Franche-Comte': u'Franche-Comté',
        'Haute-Normandie': u'Haute-Normandie',
        'Ile-de-France': u'Île-de-France',
        'Languedoc-Roussillon': u'Languedoc-Roussillon',
        'Limousin': u'Limousin',
        'Lorraine': u'Lorraine',
        'Midi-Pyrenees': u'Midi-Pyrénées',
        'Nord-Pas-de-Calais': u'Nord-Pas-de-Calais',
        'Pays-de-la-Loire': u'Pays de la Loire',
        'Picardie': u'Picardie',
        'Poitou-Charentes': u'Poitou-Charentes',
        'PACA': u'PACA',
        'Rhone-Alpes': u'Rhône-Alpes',
        'Belgique': u'Belgique',
        'Suisse': u'Suisse',
    }.items())])

    CONFIG = BackendConfig(Value('region', label=u'Region', choices=region_choices, default=''))

    def create_default_browser(self):
        region = self.config['region'].get()
        return self.create_browser(region)

    def search_events(self, query):
        return self.browser.list_events(query.start_date,
                                        query.end_date,
                                        query.city,
                                        query.categories)

    def get_event(self, _id):
        return self.browser.get_event(_id)

    def list_events(self, date_from, date_to=None):
        return self.browser.list_events(date_from, date_to)

    def fill_obj(self, event, fields):
        return self.browser.get_event(event.id, event)

    OBJECTS = {RazibusCalendarEvent: fill_obj}
