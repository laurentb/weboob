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

from collections import OrderedDict

from weboob.capabilities.job import BaseJobAdvert

from weboob.tools.backend import Module, BackendConfig
from weboob.capabilities.job import CapJob
from weboob.tools.value import Value, ValueInt

from .browser import PopolemploiBrowser

__all__ = ['PopolemploiModule']


class PopolemploiModule(Module, CapJob):
    NAME = 'popolemploi'
    DESCRIPTION = u'Pole Emploi website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    VERSION = '2.0'

    BROWSER = PopolemploiBrowser

    places_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '100|PAYS|01': u'France entière',
        '100|REGION|84': u'Auvergne-Rhône-Alpes',
        '101|DEPARTEMENT|01': u'-- Ain (01)',
        '102|DEPARTEMENT|03': u'-- Allier (03)',
        '103|DEPARTEMENT|07': u'-- Ardèche (07)',
        '104|DEPARTEMENT|15': u'-- Cantal (15)',
        '105|DEPARTEMENT|26': u'-- Drôme (26)',
        '106|DEPARTEMENT|38': u'-- Isère (38)',
        '107|DEPARTEMENT|42': u'-- Loire (42)',
        '108|DEPARTEMENT|43': u'-- Haute-Loire (43)',
        '109|DEPARTEMENT|63': u'-- Puy-de-Dôme (63)',
        '110|DEPARTEMENT|69': u'-- Rhône (69)',
        '111|DEPARTEMENT|73': u'-- Savoie (73)',
        '112|DEPARTEMENT|74': u'-- Haute-Savoie (74) ',
        '113|REGION|27': u'Bourgogne-Franche-Comté',
        '114|DEPARTEMENT|21': u'-- Côte-d\'Or (21)',
        '115|DEPARTEMENT|25': u'-- Doubs (25)',
        '116|DEPARTEMENT|39': u'-- Jura (39)',
        '117|DEPARTEMENT|58': u'-- Nièvre (58)',
        '118|DEPARTEMENT|70': u'-- Haute-Saône (70)',
        '119|DEPARTEMENT|71': u'-- Saône-et-Loire (71)',
        '120|DEPARTEMENT|89': u'-- Yonne (89)',
        '121|DEPARTEMENT|90': u'-- Territoire de Belfort (90) ',
        '122|REGION|53': u'Bretagne',
        '123|DEPARTEMENT|22': u'-- Côtes-d\'Armor (22)',
        '124|DEPARTEMENT|29': u'-- Finistère (29)',
        '125|DEPARTEMENT|35': u'-- Ille-et-Vilaine (35)',
        '126|DEPARTEMENT|56': u'-- Morbihan (56) ',
        '127|REGION|24': u'Centre-Val de Loire',
        '128|DEPARTEMENT|': u'-- Cher (18)',
        '129|DEPARTEMENT|': u'-- Eure-et-Loir (28)',
        '130|DEPARTEMENT|': u'-- Indre (36)',
        '131|DEPARTEMENT|': u'-- Indre-et-Loire (37)',
        '132|DEPARTEMENT|': u'-- Loir-et-Cher (41)',
        '133|DEPARTEMENT|': u'-- Loiret (45) ',
        '134|REGION|94': u'Corse',
        '135|DEPARTEMENT|2A': u'-- Corse-du-Sud (2A)',
        '136|DEPARTEMENT|2B': u'-- Haute-Corse (2B)',
        '137|REGION|44': u'Grand Est',
        '138|DEPARTEMENT|08': u'-- Ardennes (08)',
        '139|DEPARTEMENT|10': u'-- Aube (10)',
        '140|DEPARTEMENT|51': u'-- Marne (51)',
        '141|DEPARTEMENT|52': u'-- Haute-Marne (52)',
        '142|DEPARTEMENT|54': u'-- Meurthe-et-Moselle (54)',
        '143|DEPARTEMENT|55': u'-- Meuse (55)',
        '144|DEPARTEMENT|57': u'-- Moselle (57)',
        '145|DEPARTEMENT|67': u'-- Bas-Rhin (67)',
        '146|DEPARTEMENT|68': u'-- Haut-Rhin (68)',
        '147|DEPARTEMENT|88': u'-- Vosges (88) ',
        '148|REGION|32': u'Hauts-de-France',
        '149|DEPARTEMENT|02': u'-- Aisne (02)',
        '150|DEPARTEMENT|59': u'-- Nord (59)',
        '151|DEPARTEMENT|60': u'-- Oise (60)',
        '152|DEPARTEMENT|62': u'-- Pas-de-Calais (62)',
        '153|DEPARTEMENT|80': u'-- Somme (80) ',
        '154|REGION|11': u'Île-de-France',
        '155|DEPARTEMENT|75': u'-- Paris (75)',
        '156|DEPARTEMENT|77': u'-- Seine-et-Marne (77)',
        '157|DEPARTEMENT|78': u'-- Yvelines (78)',
        '158|DEPARTEMENT|91': u'-- Essonne (91)',
        '159|DEPARTEMENT|92': u'-- Hauts-de-Seine (92)',
        '160|DEPARTEMENT|93': u'-- Seine-Saint-Denis (93)',
        '161|DEPARTEMENT|94': u'-- Val-de-Marne (94)',
        '162|DEPARTEMENT|95': u'-- Val-d\'Oise (95) ',
        '163|REGION|28': u'Normandie',
        '164|DEPARTEMENT|14': u'-- Calvados (14)',
        '165|DEPARTEMENT|27': u'-- Eure (27)',
        '166|DEPARTEMENT|50': u'-- Manche (50)',
        '167|DEPARTEMENT|61': u'-- Orne (61)',
        '168|DEPARTEMENT|76': u'-- Seine-Maritime (76)',
        '169|REGION|75': u'Nouvelle-Aquitaine',
        '170|DEPARTEMENT|16': u'-- Charente (16)',
        '171|DEPARTEMENT|17': u'-- Charente-Maritime (17)',
        '172|DEPARTEMENT|19': u'-- Corrèze (19)',
        '173|DEPARTEMENT|23': u'-- Creuse (23)',
        '174|DEPARTEMENT|24': u'-- Dordogne (24)',
        '175|DEPARTEMENT|33': u'-- Gironde (33)',
        '176|DEPARTEMENT|40': u'-- Landes (40)',
        '177|DEPARTEMENT|47': u'-- Lot-et-Garonne (47)',
        '178|DEPARTEMENT|64': u'-- Pyrénées-Atlantiques (64)',
        '179|DEPARTEMENT|79': u'-- Deux-Sèvres (79)',
        '180|DEPARTEMENT|86': u'-- Vienne (86)',
        '181|DEPARTEMENT|87': u'-- Haute-Vienne (87) ',
        '182|REGION|76': u'Occitanie',
        '183|DEPARTEMENT|09': u'-- Ariège (09)',
        '184|DEPARTEMENT|11': u'-- Aude (11)',
        '185|DEPARTEMENT|12': u'-- Aveyron (12)',
        '186|DEPARTEMENT|30': u'-- Gard (30)',
        '187|DEPARTEMENT|31': u'-- Haute-Garonne (31)',
        '188|DEPARTEMENT|32': u'-- Gers (32)',
        '189|DEPARTEMENT|34': u'-- Hérault (34)',
        '190|DEPARTEMENT|46': u'-- Lot (46)',
        '191|DEPARTEMENT|48': u'-- Lozère (48)',
        '192|DEPARTEMENT|65': u'-- Hautes-Pyrénées (65)',
        '193|DEPARTEMENT|66': u'-- Pyrénées-Orientales (66)',
        '194|DEPARTEMENT|81': u'-- Tarn (81)',
        '195|DEPARTEMENT|82': u'-- Tarn-et-Garonne (82) ',
        '196|REGION|52': u'Pays de la Loire',
        '197|DEPARTEMENT|44': u'-- Loire-Atlantique (44)',
        '198|DEPARTEMENT|49': u'-- Maine-et-Loire (49)',
        '199|DEPARTEMENT|53': u'-- Mayenne (53)',
        '200|DEPARTEMENT|72': u'-- Sarthe (72)',
        '201|DEPARTEMENT|85': u'-- Vendée (85) ',
        '202|REGION|93': u'Provence-Alpes-Côte d\'Azur',
        '203|DEPARTEMENT|04': u'-- Alpes-de-Haute-Provence (04)',
        '204|DEPARTEMENT|05': u'-- Hautes-Alpes (05)',
        '205|DEPARTEMENT|06': u'-- Alpes-Maritimes (06)',
        '206|DEPARTEMENT|13': u'-- Bouches-du-Rhône (13)',
        '207|DEPARTEMENT|83': u'-- Var (83)',
        '208|DEPARTEMENT|84': u'-- Vaucluse (84)',
        '209|REGION|01': u'Guadeloupe',
        '210|REGION|02': u'Martinique',
        '211|REGION|03': u'Guyane',
        '212|REGION|04': u'La Réunion',
        '213|REGION|05': u'Mayotte',
        '214|DEPARTEMENT|975': u'Saint-Pierre-et-Miquelon',
        '215|DEPARTEMENT|977': u'Saint-Barthélemy',
        '216|DEPARTEMENT|978': u'Saint-Martin',
        '217|DEPARTEMENT|986': u'Wallis-et-Futuna',
        '218|DEPARTEMENT|987': u'Polynésie française',
        '219|DEPARTEMENT|988': u'Nouvelle-Calédonie',
        '220|DEPARTEMENT|989': u'Clipperton',
    }.items())])

    type_contrat_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        ' ': u'Tous types de contrats',
        'CDI': u'CDI tout public',
        'CDI&natureOffre=E2': u'CDI alternance',
        'CDI&natureOffre=FS': u'CDI insertion',
        'CDD': u'CDD tout public',
        'CDD&natureOffre=E2': u'CDD alternance',
        'CDD&natureOffre=FS': u'CDD insertion',
        'CDS': u'CDD Senior',
        'MID': u'Mission d\'intérim',
        'SAI': u'Contrat de travail saisonnier',
        'INT': u'Contrat de travail intermittent',
        'FRA': u'Franchise',
        'LIB': u'Profession libérale',
        'REP': u'Reprise d\'entreprise',
        'CCE': u'Profession commerciale',
    }.items())])

    qualification_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        ' ': u'Toute Qualification',
        '1': u'Manoeuvre',
        '2': u'Ouvrier spécialisé',
        '3': u'Ouvrier qualifié (P1,P2)',
        '4': u'Ouvrier qualifié (P3,P4,OHQ)',
        '5': u'Employé non qualifié',
        '6': u'Employé qualifié',
        '7': u'Technicien',
        '8': u'Agent de maîtrise',
        '9': u'Cadre',
    }.items())])

    limit_date_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        ' ': u'Aucune limite',
        '1': u'Hier',
        '3': u'3 jours',
        '7': u'1 semaine',
        '14': u'2 semaines',
        '31': u'1 mois',
        '93': u'3 mois',
    }.items())])

    domain_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        ' ': u'Tout secteur d\'activité',
        'M': u'Achats / Comptabilité / Gestion',
        'B': u'Arts / Artisanat d\'art',
        'C': u'Banque / Assurance',
        'F': u'Bâtiment / Travaux Publics',
        'D': u'Commerce / Vente',
        'E': u'Communication / Multimédia',
        'M14': u'Conseil / Etudes',
        'M13': u'Direction d\'entreprise',
        'A': u'Espaces verts et naturels / Agriculture / Pêche / Soins aux animaux',
        'G': u'Hôtellerie - Restauration / Tourisme / Animation',
        'C15': u'Immobilier',
        'H': u'Industrie',
        'M18': u'Informatique / Télécommunication',
        'I': u'Installation / Maintenance',
        'M17': u'Marketing / Stratégie commerciale',
        'M15': u'Ressources Humaines',
        'J': u'Santé',
        'M16': u'Secrétariat / Assistanat',
        'K': u'Services à la personne / à la collectivité',
        'L': u'Spectacle',
        'L14': u'Sport',
        'N': u'Transport / Logistique'
    }.items())])

    CONFIG = BackendConfig(Value('metier', label='Job name', masked=False, default=''),
                           Value('place', label=u'Place', choices=places_choices, default='100|FRANCE|01'),
                           Value('contrat', label=u'Contract', choices=type_contrat_choices, default=''),
                           ValueInt('salary', label=u'Salary/Year', default=0),
                           Value('qualification', label=u'Qualification', choices=qualification_choices, default=''),
                           Value('limit_date', label=u'Date limite', choices=limit_date_choices, default=''),
                           Value('domain', label=u'Domain', choices=domain_choices, default=''))

    def search_job(self, pattern=None):
        return self.browser.search_job(pattern=pattern)

    def advanced_search_job(self):
        return self.browser.advanced_search_job(metier=self.config['metier'].get(),
                                                place=self.config['place'].get(),
                                                contrat=self.config['contrat'].get(),
                                                salary=self.config['salary'].get(),
                                                qualification=self.config['qualification'].get(),
                                                limit_date=self.config['limit_date'].get(),
                                                domain=self.config['domain'].get())

    def get_job_advert(self, _id, advert=None):
        return self.browser.get_job_advert(_id, advert)

    def fill_obj(self, advert, fields):
        return self.get_job_advert(advert.id, advert)

    OBJECTS = {BaseJobAdvert: fill_obj}
