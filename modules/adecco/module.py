# -*- coding: utf-8 -*-

# Copyright(C) 2013      Bezleputh
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
from weboob.tools.value import Value
from weboob.capabilities.job import CapJob, BaseJobAdvert
from .browser import AdeccoBrowser

__all__ = ['AdeccoModule']


class AdeccoModule(Module, CapJob):
    NAME = 'adecco'
    DESCRIPTION = u'adecco website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    VERSION = '1.3'

    BROWSER = AdeccoBrowser

    publicationDate_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '000000': u'-- Indifferent --',
        '2': u'Moins de 48 heures',
        '7': u'Moins de 1 semaine',
        '14': u'Moins de 2 semaines',
    }.items())])

    type_contract_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '': u'-- Indifferent --',
        'ADCFREMP005': u'CDD',
        'ADCFREMP004': u'CDI',
        'ADCFREMP003': u'Intérim',
        'ADCFREMP009': u'Autres',
        'ADCFREMP010': u'Libéral',
    }.items())])

    places_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '': u'-- Indifferent --',
        'AIN': u'Ain',
        'AISNE': u'Aisne',
        'ALLIER': u'Allier',
        'ALPES-DE-HAUTE-PROVENCE': u'Alpes-De-Haute-Provence',
        'ALPES-MARITIMES': u'Alpes-Maritimes',
        'ARDECHE': u'Ardeche',
        'ARDENNES': u'Ardennes',
        'ARIEGE': u'Ariege',
        'AUBE': u'Aube',
        'AUDE': u'Aude',
        'AVEYRON': u'Aveyron',
        'BAS-RHIN': u'Bas-Rhin',
        'BOUCHES-DU-RHONE': u'Bouches-Du-Rhone',
        'CALVADOS': u'Calvados',
        'CANTAL': u'Cantal',
        'CHARENTE': u'Charente',
        'CHARENTE-MARITIME': u'Charente-Maritime',
        'CHER': u'Cher',
        'CORREZE': u'Correze',
        'CORSE-DU-SUD': u'Corse du Sud',
        'COTE-D%27OR': u'Cote D\'Or',
        'COTES-D%27ARMOR': u'Cotes D\'Armor',
        'CREUSE': u'Creuse',
        'DEUX-SEVRES': u'Deux-Sevres',
        'DORDOGNE': u'Dordogne',
        'DOUBS': u'Doubs',
        'DROME': u'Drome',
        'ESSONNE': u'Essonne',
        'EURE': u'Eure',
        'EURE-ET-LOIR': u'Eure-Et-Loir',
        'FINISTERE': u'Finistere',
        'GARD': u'Gard',
        'GERS': u'Gers',
        'GIRONDE': u'Gironde',
        'GUADELOUPE': u'Guadeloupe',
        'GUYANE': u'Guyane',
        'HAUT-RHIN': u'Haut-Rhin',
        'HAUTE-CORSE': u'Haute-Corse',
        'HAUTE-GARONNE': u'Haute-Garonne',
        'HAUTE-LOIRE': u'Haute-Loire',
        'HAUTE-MARNE': u'Haute-Marne',
        'HAUTE-SAONE': u'Haute-Saone',
        'HAUTE-SAVOIE': u'Haute-Savoie',
        'HAUTE-VIENNE': u'Haute-Vienne',
        'HAUTES-ALPES': u'Hautes-Alpes',
        'HAUTES-PYRENEES': u'Hautes-Pyrenees',
        'HAUTS-DE-SEINE': u'Hauts-De-Seine',
        'HERAULT': u'Herault',
        'ILLE-ET-VILAINE': u'Ille-Et-Vilaine',
        'INDRE': u'Indre',
        'INDRE-ET-LOIRE': u'Indre-Et-Loire',
        'ISERE': u'Isere',
        'JURA': u'Jura',
        'LA+REUNION': u'La Reunion',
        'LANDES': u'Landes',
        'LOIR-ET-CHER': u'Loir-Et-Cher',
        'LOIRE': u'Loire',
        'LOIRE-ATLANTIQUE': u'Loire-Atlantique',
        'LOIRET': u'Loiret',
        'LOT': u'Lot',
        'LOT-ET-GARONNE': u'Lot-Et-Garonne',
        'LOZERE': u'Lozere',
        'MAINE-ET-LOIRE': u'Maine-Et-Loire',
        'MANCHE': u'Manche',
        'MARNE': u'Marne',
        'MARTINIQUE': u'Martinique',
        'MAYENNE': u'Mayenne',
        'MAYOTTE': u'Mayotte',
        'MEURTHE-ET-MOSELLE': u'Meurthe et Moselle',
        'MEUSE': u'Meuse',
        'MONACO': u'Monaco',
        'MORBIHAN': u'Morbihan',
        'MOSELLE': u'Moselle',
        'NIEVRE': u'Nievre',
        'NORD': u'Nord',
        'OISE': u'Oise',
        'ORNE': u'Orne',
        'PARIS': u'Paris',
        'PAS-DE-CALAIS': u'Pas-de-Calais',
        'PUY-DE-DOME': u'Puy-de-Dome',
        'PYRENEES-ATLANTIQUES': u'Pyrenees-Atlantiques',
        'PYRENEES-ORIENTALES': u'Pyrenees-Orientales',
        'RHONE': u'Rhone',
        'SAONE-ET-LOIRE': u'Saone-et-Loire',
        'SARTHE': u'Sarthe',
        'SAVOIE': u'Savoie',
        'SEINE-ET-MARNE': u'Seine-et-Marne',
        'SEINE-MARITIME': u'Seine-Maritime',
        'SEINE-SAINT-DENIS': u'Seine-Saint-Denis',
        'SOMME': u'Somme',
        'ST+PIERRE+ET+MIQUELON': u'St Pierre et Miquelon',
        'SUISSE': u'Suisse',
        'TARN': u'Tarn',
        'TARN-ET-GARONNE': u'Tarn-et-Garonne',
        'TERRITOIRE+DE+BELFORT': u'Territoire de Belfort',
        'VAL-D%27OISE': u'Val-D\'Oise',
        'VAL-DE-MARNE': u'Val-De-Marne',
        'VAR': u'Var',
        'VAUCLUSE': u'Vaucluse',
        'VENDEE': u'Vendee',
        'VIENNE': u'Vienne',
        'VOSGES': u'Vosges',
        'YONNE': u'Yonne',
        'YVELINES': u'Yvelines',
    }.items())])

    activityDomain_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        'Z': '-- Indifferent --',
        'A': u'Accueil - Secrétariat - Fonctions Administratives',
        'B': u'Achats - Juridique - Qualité - RH - Direction',
        'C': u'Agriculture - Viticulture - Pêche - Espaces Verts',
        'D': u'Automobile',
        'E': u'Banque - Finance - Gestion Comptabilité - Assurance',
        'F': u'Bâtiment - Travaux Publics - Architecture - Immobilier',
        'G': u'Bureaux d\'Etudes - Méthodes',
        'H': u'Commerce - Vente - Grande Distribution',
        'I': u'Environnement - Nettoyage - Sécurité',
        'J': u'Hôtellerie - Restauration - Métiers de Bouche',
        'K': u'Industrie',
        'L': u'Informatique - Technologie de l\'Information',
        'M': u'Logistique - Manutention - Transport',
        'N': u'Marketing - Communication - Imprimerie - Edition',
        'O': u'Médical - Paramédical - Esthétique',
        'P': u'Pharmacie (Industrie, Officine) - Recherche clinique',
        'Q': u'Télémarketing - Téléservices',
        'R': u'Tourisme - Loisirs - Spectacle - Audiovisuel',
    }.items())])

    CONFIG = BackendConfig(Value('job', label='Job name', masked=False, default=''),
                           Value('town', label='Town name', masked=False, default=''),
                           Value('place', label=u'County', choices=places_choices),
                           Value('publication_date', label=u'Publication Date', choices=publicationDate_choices),
                           Value('contract', labe=u'Contract type', choices=type_contract_choices),
                           Value('activity_domain', label=u'Activity Domain', choices=activityDomain_choices,
                                 default=''),
                           )

    def search_job(self, pattern=None):
        for advert in self.browser.search_job(pattern):
            yield advert

    def advanced_search_job(self):
        activity_domain = self.config['activity_domain'].get() if self.config['activity_domain'].get() != u'Z' else None

        for advert in self.browser.advanced_search_job(publication_date=int(self.config['publication_date'].get()),
                                                       contract_type=self.config['contract'].get(),
                                                       conty=self.config['place'].get(),
                                                       activity_domain=activity_domain,
                                                       job=self.config['job'].get(),
                                                       town=self.config['town'].get()
                                                       ):
            yield advert

    def get_job_advert(self, _id, advert=None):
        return self.browser.get_job_advert(_id, advert)

    def fill_obj(self, advert, fields):
        return self.get_job_advert(advert.id, advert)

    OBJECTS = {BaseJobAdvert: fill_obj}
