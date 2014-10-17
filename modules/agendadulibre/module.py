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
from weboob.capabilities.calendar import CapCalendarEvent, CATEGORIES
from weboob.tools.ordereddict import OrderedDict
from weboob.tools.value import Value

from .browser import AgendadulibreBrowser


__all__ = ['AgendadulibreModule']


class AgendadulibreModule(Module, CapCalendarEvent):
    NAME = 'agendadulibre'
    DESCRIPTION = u'agendadulibre website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    LICENSE = 'AGPLv3+'
    VERSION = '1.1'
    ASSOCIATED_CATEGORIES = [CATEGORIES.CONF]
    BROWSER = AgendadulibreBrowser

    region_choices = OrderedDict([(k, u'%s (%s)' % (v, k)) for k, v in sorted({
        "http://www.agendadulibre.org": u'--France--',
        "http://www.agendadulibre.org#1": u'Alsace',
        "http://www.agendadulibre.org#2": u'Aquitaine',
        "http://www.agendadulibre.org#3": u'Auvergne',
        "http://www.agendadulibre.org#4": u'Basse-Normandie',
        "http://www.agendadulibre.org#5": u'Bourgogne',
        "http://www.agendadulibre.org#6": u'Bretagne',
        "http://www.agendadulibre.org#7": u'Centre',
        "http://www.agendadulibre.org#8": u'Champagne-Ardenne',
        "http://www.agendadulibre.org#9": u'Corse',
        "http://www.agendadulibre.org#10": u'Franche-Comté',
        "http://www.agendadulibre.org#23": u'Guadeloupe',
        "http://www.agendadulibre.org#24": u'Guyane',
        "http://www.agendadulibre.org#11": u'Haute-Normandie',
        "http://www.agendadulibre.org#12": u'Île-de-France',
        "http://www.agendadulibre.org#13": u'Languedoc-Roussillon',
        "http://www.agendadulibre.org#14": u'Limousin',
        "http://www.agendadulibre.org#15": u'Lorraine',
        "http://www.agendadulibre.org#25": u'Martinique',
        "http://www.agendadulibre.org#16": u'Midi-Pyrénées',
        "http://www.agendadulibre.org#17": u'Nord-Pas-de-Calais',
        "http://www.agendadulibre.org#18": u'Pays de la Loire',
        "http://www.agendadulibre.org#19": u'Picardie',
        "http://www.agendadulibre.org#20": u'Poitou-Charentes',
        "http://www.agendadulibre.org#21": u'Provence-Alpes-Côte d\'Azur',
        "http://www.agendadulibre.org#26": u'Réunion',
        "http://www.agendadulibre.org#22": u'Rhône-Alpes',
        "http://www.agendadulibre.be": u'--Belgique--',
        "http://www.agendadulibre.be#11": u'Antwerpen',
        "http://www.agendadulibre.be#10": u'Brabant wallon',
        "http://www.agendadulibre.be#9": u'Bruxelles-Capitale',
        "http://www.agendadulibre.be#8": u'Hainaut',
        "http://www.agendadulibre.be#7": u'Liege',
        "http://www.agendadulibre.be#6": u'Limburg',
        "http://www.agendadulibre.be#5": u'Luxembourg',
        "http://www.agendadulibre.be#4": u'Namur',
        "http://www.agendadulibre.be#3": u'Oost-Vlaanderen',
        "http://www.agendadulibre.be#2": u'Vlaams-Brabant',
        "http://www.agendadulibre.be#1": u'West-Vlaanderen',
        "http://www.agendadulibre.ch": u'--Suisse--',
        "http://www.agendadulibre.ch#15": u'Appenzell Rhodes-Extérieures',
        "http://www.agendadulibre.ch#16": u'Appenzell Rhodes-Intérieures',
        "http://www.agendadulibre.ch#19": u'Argovie',
        "http://www.agendadulibre.ch#13": u'Bâle-Campagne',
        "http://www.agendadulibre.ch#12": u'Bâle-Ville',
        "http://www.agendadulibre.ch#2": u'Berne',
        "http://www.agendadulibre.ch#10": u'Fribourg',
        "http://www.agendadulibre.ch#25": u'Genève',
        "http://www.agendadulibre.ch#8": u'Glaris',
        "http://www.agendadulibre.ch#18": u'Grisons',
        "http://www.agendadulibre.ch#26": u'Jura',
        "http://www.agendadulibre.ch#3": u'Lucerne',
        "http://www.agendadulibre.ch#24": u'Neuchâtel',
        "http://www.agendadulibre.ch#7": u'Nidwald',
        "http://www.agendadulibre.ch#6": u'Obwald',
        "http://www.agendadulibre.ch#17": u'Saint-Gall',
        "http://www.agendadulibre.ch#14": u'Schaffhouse',
        "http://www.agendadulibre.ch#5": u'Schwytz',
        "http://www.agendadulibre.ch#11": u'Soleure',
        "http://www.agendadulibre.ch#21": u'Tessin',
        "http://www.agendadulibre.ch#20": u'Thurgovie',
        "http://www.agendadulibre.ch#4": u'Uri',
        "http://www.agendadulibre.ch#23": u'Valais',
        "http://www.agendadulibre.ch#22": u'Vaud',
        "http://www.agendadulibre.ch#9": u'Zoug',
        "http://www.agendadulibre.ch#1": u'Zurich',
    }.iteritems())])

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
        return self.browser.get_event(event.id, event)

    OBJECTS = {AgendadulibreBrowser: fill_obj}
