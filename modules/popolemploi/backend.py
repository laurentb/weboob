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


from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.capabilities.job import ICapJob
from weboob.tools.value import Value
from weboob.tools.ordereddict import OrderedDict

from .browser import PopolemploiBrowser
from .job import PopolemploiJobAdvert

__all__ = ['PopolemploiBackend']


class PopolemploiBackend(BaseBackend, ICapJob):
    NAME = 'popolemploi'
    DESCRIPTION = u'Pole Emploi website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    VERSION = '0.h'

    BROWSER = PopolemploiBrowser

    places_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '': u'Tout type de lieux',
        'FRANCE_01': u'France entière',
        'REGION_42': u'Alsace',
        'DEPARTEMENT_67': u'-- Rhin (Bas) (67)',
        'DEPARTEMENT_68': u'-- Rhin (Haut) (68)',
        'REGION_72': u'Aquitaine',
        'DEPARTEMENT_24': u'-- Dordogne (24)',
        'DEPARTEMENT_33': u'-- Gironde (33)',
        'DEPARTEMENT_40': u'-- Landes (40)',
        'DEPARTEMENT_47': u'-- Lot et Garonne (47)',
        'DEPARTEMENT_64': u'-- Pyrénées Atlantiques (64)',
        'REGION_83': u'Auvergne',
        'DEPARTEMENT_03': u'-- Allier (03)',
        'DEPARTEMENT_15': u'-- Cantal (15)',
        'DEPARTEMENT_43': u'-- Loire (Haute) (43)',
        'DEPARTEMENT_63': u'-- Puy de Dôme (63)',
        'REGION_26': u'Bourgogne',
        'DEPARTEMENT_21': u'-- Côte d\'Or (21)',
        'DEPARTEMENT_58': u'-- Nièvre (58)',
        'DEPARTEMENT_71': u'-- Saône et Loire (71)',
        'DEPARTEMENT_89': u'-- Yonne (89)',
        'REGION_53': u'Bretagne',
        'DEPARTEMENT_22': u'-- Côtes d\'Armor (22)',
        'DEPARTEMENT_29': u'-- Finistère (29)',
        'DEPARTEMENT_35': u'-- Ille et Vilaine (35)',
        'DEPARTEMENT_56': u'-- Morbihan (56)',
        'REGION_24': u'Centre',
        'DEPARTEMENT_18': u'-- Cher (18)',
        'DEPARTEMENT_28': u'-- Eure etLoir (28)',
        'DEPARTEMENT_36': u'-- Indre (36)',
        'DEPARTEMENT_37': u'-- Indre et Loire (37)',
        'DEPARTEMENT_41': u'-- Loir et Cher (41)',
        'DEPARTEMENT_45': u'-- Loiret (45)',
        'REGION_21': u'Champagne Ardenne',
        'DEPARTEMENT_08': u'-- Ardennes (08)',
        'DEPARTEMENT_10': u'-- Aube (10)',
        'DEPARTEMENT_51': u'-- Marne (51)',
        'DEPARTEMENT_52': u'-- Marne (Haute) (52)',
        'REGION_94': u'Corse',
        'DEPARTEMENT_2A': u'-- Corse du Sud (2A)',
        'DEPARTEMENT_2B': u'-- Haute Corse (2B)',
        'REGION_43': u'Franche Comté',
        'DEPARTEMENT_90': u'-- Belfort (Territoire de) (90)',
        'DEPARTEMENT_25': u'-- Doubs (25)',
        'DEPARTEMENT_39': u'-- Jura (39)',
        'DEPARTEMENT_70': u'-- Saône (Haute) (70)',
        'REGION_11': u'Ile de France',
        'DEPARTEMENT_91': u'-- Essonne (91)',
        'DEPARTEMENT_92': u'-- Hauts de Seine (92)',
        'DEPARTEMENT_75': u'-- Paris (Dept.) (75)',
        'DEPARTEMENT_93': u'-- Seine Saint Denis (93)',
        'DEPARTEMENT_77': u'-- Seine et Marne (77)',
        'DEPARTEMENT_95': u'-- Val d\'Oise (95)',
        'DEPARTEMENT_94': u'-- Val de Marne (94)',
        'DEPARTEMENT_78': u'-- Yvelines (78)',
        'REGION_91': u'Languedoc Roussillon',
        'DEPARTEMENT_11': u'-- Aude (11)',
        'DEPARTEMENT_30': u'-- Gard (30)',
        'DEPARTEMENT_34': u'-- Hérault (34)',
        'DEPARTEMENT_48': u'-- Lozère (48)',
        'DEPARTEMENT_66': u'-- Pyrénées Orientales (66)',
        'REGION_74': u'Limousin',
        'DEPARTEMENT_19': u'-- Corrèze (19)',
        'DEPARTEMENT_23': u'-- Creuse (23)',
        'DEPARTEMENT_87': u'-- Vienne (Haute) (87)',
        'REGION_41': u'Lorraine',
        'DEPARTEMENT_54': u'-- Meurthe et Moselle (54)',
        'DEPARTEMENT_55': u'-- Meuse (55)',
        'DEPARTEMENT_57': u'-- Moselle (57)',
        'DEPARTEMENT_88': u'-- Vosges (88)',
        'REGION_73': u'Midi Pyrénées',
        'DEPARTEMENT_09': u'-- Ariège (09)',
        'DEPARTEMENT_12': u'-- Aveyron (12)',
        'DEPARTEMENT_31': u'-- Garonne (Haute) (31)',
        'DEPARTEMENT_32': u'-- Gers (32)',
        'DEPARTEMENT_46': u'-- Lot (46)',
        'DEPARTEMENT_65': u'-- Pyrénées (Hautes) (65)',
        'DEPARTEMENT_81': u'-- Tarn (81)',
        'DEPARTEMENT_82': u'-- Tarn et Garonne (82)',
        'REGION_31': u'Nord Pas de Calais',
        'DEPARTEMENT_59': u'-- Nord (59)',
        'DEPARTEMENT_62': u'-- Pas de Calais (62)',
        'REGION_25': u'Normandie (Basse)',
        'DEPARTEMENT_14': u'-- Calvados (14)',
        'DEPARTEMENT_50': u'-- Manche (50)',
        'DEPARTEMENT_61': u'-- Orne (61)',
        'REGION_23': u'Normandie (Haute)',
        'DEPARTEMENT_27': u'-- Eure (27)',
        'DEPARTEMENT_76': u'-- Seine Maritime (76)',
        'REGION_52': u'Pays de la Loire',
        'DEPARTEMENT_44': u'-- Loire Atlantique (44)',
        'DEPARTEMENT_49': u'-- Maine et Loire (49)',
        'DEPARTEMENT_53': u'-- Mayenne (53)',
        'DEPARTEMENT_72': u'-- Sarthe (72)',
        'DEPARTEMENT_85': u'-- Vendée (85)',
        'REGION_22': u'Picardie',
        'DEPARTEMENT_02': u'-- Aisne (02)',
        'DEPARTEMENT_60': u'-- Oise (60)',
        'DEPARTEMENT_80': u'-- Somme (80)',
        'REGION_54': u'Poitou Charentes',
        'DEPARTEMENT_16': u'-- Charente (16)',
        'DEPARTEMENT_17': u'-- Charente Maritime (17)',
        'DEPARTEMENT_79': u'-- Sèvres (Deux) (79)',
        'DEPARTEMENT_86': u'-- Vienne (86)',
        'REGION_93': u'Provence Alpes Côte d\'Azur',
        'DEPARTEMENT_05': u'-- Alpes (Hautes) (05)',
        'DEPARTEMENT_06': u'-- Alpes Maritimes (06)',
        'DEPARTEMENT_04': u'-- Alpes de Haute Provence (04)',
        'DEPARTEMENT_13': u'-- Bouches du Rhône (13)',
        'DEPARTEMENT_83': u'-- Var (83)',
        'DEPARTEMENT_84': u'-- Vaucluse (84)',
        'REGION_82': u'Rhône Alpes',
        'DEPARTEMENT_01': u'-- Ain (01)',
        'DEPARTEMENT_07': u'-- Ardèche (07)',
        'DEPARTEMENT_26': u'-- Drôme (26)',
        'DEPARTEMENT_38': u'-- Isère (38)',
        'DEPARTEMENT_42': u'-- Loire (42)',
        'DEPARTEMENT_69': u'-- Rhône (69)',
        'DEPARTEMENT_73': u'-- Savoie (73)',
        'DEPARTEMENT_74': u'-- Savoie (Haute) (74)',
        'REGION_96': u'Région Antilles / Guyane',
        'DEPARTEMENT_971': u'-- Guadeloupe (971)',
        'DEPARTEMENT_973': u'-- Guyane (973)',
        'DEPARTEMENT_972': u'-- Martinique (972)',
        'DEPARTEMENT_977': u'-- Saint Barthélémy (977)',
        'DEPARTEMENT_978': u'-- Saint Martin (978)',
        'REGION_98': u'Région Atlantique Nord',
        'DEPARTEMENT_975': u'-- Saint Pierre et Miquelon (975)',
        'REGION_95': u'Région Pacifique',
        'DEPARTEMENT_989': u'-- Ile de Clipperton (989)',
        'DEPARTEMENT_988': u'-- Nouvelle Calédonie (988)',
        'DEPARTEMENT_987': u'-- Polynésie française (987)',
        'DEPARTEMENT_984': u'-- Terres australes/antarctiques (984)',
        'DEPARTEMENT_986': u'-- Wallis et Futuna (986)',
        'REGION_97': u'Région Réunion / Mayotte',
        'DEPARTEMENT_976': u'-- Mayotte (976)',
        'DEPARTEMENT_974': u'-- Réunion (974)',
    }.iteritems())])

    type_contrat_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        ' ': u'Tous types de contrats',
        '11': u'CDI tout public',
        '14': u'CDI alternance',
        '13': u'CDI insertion',
        '12': u'CDD tout public',
        '16': u'CDD alternance',
        '15': u'CDD insertion',
        '10': u'CDD Senior',
        '3': u'Mission d\'intérim',
        '4': u'Contrat de travail saisonnier',
        '5': u'Contrat de travail intermittent',
        '8': u'Franchise',
        '7': u'Profession libérale',
        '9': u'Reprise d\'entreprise',
        '6': u'Profession commerciale',
    }.iteritems())])

    CONFIG = BackendConfig(Value('metier', label='Job name', masked=False, default=''),
                           Value('place', label=u'Place', choices=places_choices, default='FRANCE_01'),
                           Value('contrat', label=u'Contract', choices=type_contrat_choices, default=''))

    def search_job(self, pattern=None):
        with self.browser:
            return self.browser.search_job(pattern=pattern,
                                           metier=self.config['metier'].get(),
                                           place=self.config['place'].get(),
                                           contrat=self.config['contrat'].get())

    def get_job_advert(self, _id, advert=None):
        with self.browser:
            return self.browser.get_job_advert(_id, advert)

    def fill_obj(self, advert, fields):
        self.get_job_advert(advert.id, advert)

    OBJECTS = {PopolemploiJobAdvert: fill_obj}
