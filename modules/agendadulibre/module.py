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

from .browser import AgendadulibreBrowser


__all__ = ['AgendadulibreModule']


class AgendadulibreModule(Module, CapCalendarEvent):
    NAME = 'agendadulibre'
    DESCRIPTION = u'agendadulibre website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    LICENSE = 'AGPLv3+'
    VERSION = '1.5'
    ASSOCIATED_CATEGORIES = [CATEGORIES.CONF]
    BROWSER = AgendadulibreBrowser

    region_choices = OrderedDict([(k, u'%s (%s)' % (v, k)) for k, v in sorted({
        "https://www.agendadulibre.org": u'--France--',
        "https://www.agendadulibre.org#3": u'Auvergne-Rhône-Alpes',
        "https://www.agendadulibre.org#5": u'Bourgogne-Franche-Comté',
        "https://www.agendadulibre.org#6": u'Bretagne',
        "https://www.agendadulibre.org#7": u'Centre-Val de Loire',
        "https://www.agendadulibre.org#30": u'Collectivité sui generis',
        "https://www.agendadulibre.org#29": u'Collectivités d\'outre-mer',
        "https://www.agendadulibre.org#9": u'Corse',
        "https://www.agendadulibre.org#1": u'Grand Est',
        "https://www.agendadulibre.org#23": u'Guadeloupe',
        "https://www.agendadulibre.org#24": u'Guyane',
        "https://www.agendadulibre.org#17": u'Hauts-de-France',
        "https://www.agendadulibre.org#12": u'Île-de-France',
        "https://www.agendadulibre.org#31": u'Internet',
        "https://www.agendadulibre.org#26": u'La Réunion',
        "https://www.agendadulibre.org#25": u'Martinique',
        "https://www.agendadulibre.org#28": u'Mayotte',
        "https://www.agendadulibre.org#4": u'Normandie',
        "https://www.agendadulibre.org#2": u'Nouvelle-Aquitaine',
        "https://www.agendadulibre.org#13": u'Occitanie',
        "https://www.agendadulibre.org#18": u'Pays de la Loire',
        "https://www.agendadulibre.org#21": u'Provence-Alpes-Côte d\'Azur',
        "https://www.agendadulibre.be": u'--Belgique--',
        "https://www.agendadulibre.be#11": u'Antwerpen',
        "https://www.agendadulibre.be#10": u'Brabant wallon',
        "https://www.agendadulibre.be#9": u'Bruxelles-Capitale',
        "https://www.agendadulibre.be#8": u'Hainaut',
        "https://www.agendadulibre.be#7": u'Liege',
        "https://www.agendadulibre.be#6": u'Limburg',
        "https://www.agendadulibre.be#5": u'Luxembourg',
        "https://www.agendadulibre.be#4": u'Namur',
        "https://www.agendadulibre.be#3": u'Oost-Vlaanderen',
        "https://www.agendadulibre.be#2": u'Vlaams-Brabant',
        "https://www.agendadulibre.be#1": u'West-Vlaanderen',
        "https://www.agendadulibre.ch": u'--Suisse--',
        "https://www.agendadulibre.ch#15": u'Appenzell Rhodes-Extérieures',
        "https://www.agendadulibre.ch#16": u'Appenzell Rhodes-Intérieures',
        "https://www.agendadulibre.ch#19": u'Argovie',
        "https://www.agendadulibre.ch#13": u'Bâle-Campagne',
        "https://www.agendadulibre.ch#12": u'Bâle-Ville',
        "https://www.agendadulibre.ch#2": u'Berne',
        "https://www.agendadulibre.ch#10": u'Fribourg',
        "https://www.agendadulibre.ch#25": u'Genève',
        "https://www.agendadulibre.ch#8": u'Glaris',
        "https://www.agendadulibre.ch#18": u'Grisons',
        "https://www.agendadulibre.ch#26": u'Jura',
        "https://www.agendadulibre.ch#3": u'Lucerne',
        "https://www.agendadulibre.ch#24": u'Neuchâtel',
        "https://www.agendadulibre.ch#7": u'Nidwald',
        "https://www.agendadulibre.ch#6": u'Obwald',
        "https://www.agendadulibre.ch#17": u'Saint-Gall',
        "https://www.agendadulibre.ch#14": u'Schaffhouse',
        "https://www.agendadulibre.ch#5": u'Schwytz',
        "https://www.agendadulibre.ch#11": u'Soleure',
        "https://www.agendadulibre.ch#21": u'Tessin',
        "https://www.agendadulibre.ch#20": u'Thurgovie',
        "https://www.agendadulibre.ch#4": u'Uri',
        "https://www.agendadulibre.ch#23": u'Valais',
        "https://www.agendadulibre.ch#22": u'Vaud',
        "https://www.agendadulibre.ch#9": u'Zoug',
        "https://www.agendadulibre.ch#1": u'Zurich',
    }.items())])

    CONFIG = BackendConfig(Value('region', label=u'Region', choices=region_choices))

    def create_default_browser(self):
        choice = self.config['region'].get().split('#')
        selected_region = '' if len(choice) < 2 else choice[-1]
        return self.create_browser(website=choice[0], region=selected_region)

    def search_events(self, query):
        return self.browser.list_events(query.start_date,
                                        query.end_date,
                                        query.city,
                                        query.categories)

    def list_events(self, date_from, date_to=None):
        return self.browser.list_events(date_from, date_to)

    def get_event(self, event_id):
        return self.browser.get_event(event_id)

    def fill_obj(self, event, fields):
        event = self.browser.get_event(event.id, event)
        choice = self.config['region'].get().split('#')
        selected_region = '' if len(choice) < 2 else choice[-1]
        if selected_region == '23':
            event.timezone = 'America/Guadeloupe'
        elif selected_region == '24':
            event.timezone = 'America/Guyana'
        elif selected_region == '26':
            event.timezone = 'Indian/Reunion'
        elif selected_region == '25':
            event.timezone = 'America/Martinique'
        else:
            event.timezone = 'Europe/Paris'
        return event

    OBJECTS = {AgendadulibreBrowser: fill_obj}
