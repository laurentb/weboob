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
from weboob.tools.ordereddict import OrderedDict
from weboob.tools.value import Value
from weboob.capabilities.job import ICapJob
from .browser import AdeccoBrowser
from .job import AdeccoJobAdvert

__all__ = ['AdeccoBackend']


class AdeccoBackend(BaseBackend, ICapJob):
    NAME = 'adecco'
    DESCRIPTION = u'adecco website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    VERSION = '0.h'

    BROWSER = AdeccoBrowser

    publicationDate_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '000000': u'-- Indifférent --',
        '1': u'Moins de 48 heures',
        '2': u'Moins de 1 semaine',
        '4': u'Moins de 2 semaines',
        '3': u'Moins de 5 semaines',
    }.iteritems())])

    searchCounty_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '000000': u'Tous les départements',
        '95': u'Ain (01)',
        '81': u'Aisne (02)',
        '8': u'Allier (03)',
        '89': u'Alpes-de-Haute-Provence (04)',
        '91': u'Alpes-Maritimes (06)',
        '104': u'Andorre (991)',
        '96': u'Ardèche (07)',
        '29': u'Ardennes (08)',
        '66': u'Ariège (09)',
        '30': u'Aube (10)',
        '54': u'Aude (11)',
        '67': u'Aveyron (12)',
        '1': u'Bas-Rhin (67)',
        '92': u'Bouches-du-Rhône (13)',
        '12': u'Calvados (14)',
        '9': u'Cantal (15)',
        '85': u'Charente (16)',
        '86': u'Charente-Maritime (17)',
        '23': u'Cher (18)',
        '59': u'Corrèze (19)',
        '33': u'Corse-du-Sud (2A)',
        '15': u'Côte-d\'Or (21)',
        '19': u'Côtes-d\'Armor (22)',
        '60': u'Creuse (23)',
        '87': u'Deux-Sèvres (79)',
        '3': u'Dordogne (24)',
        '40': u'Doubs (25)',
        '97': u'Drôme (26)',
        '49': u'Essonne (91)',
        '44': u'Eure (27)',
        '24': u'Eure-et-Loir (28)',
        '20': u'Finistère (29)',
        '55': u'Gard (30)',
        '69': u'Gers (32)',
        '4': u'Gironde (33)',
        '35': u'Guadeloupe (971)',
        '37': u'Guyane (973)',
        '34': u'Haute-Corse (2B)',
        '68': u'Haute-Garonne (31)',
        '10': u'Haute-Loire (43)',
        '32': u'Haute-Marne (52)',
        '90': u'Hautes-Alpes (05)',
        '42': u'Haute-Saône (70)',
        '102': u'Haute-Savoie (74)',
        '71': u'Hautes-Pyrénées (65)',
        '61': u'Haute-Vienne (87)',
        '2': u'Haut-Rhin (68)',
        '50': u'Hauts-de-Seine (92)',
        '56': u'Hérault (34)',
        '21': u'Ille-et-Vilaine (35)',
        '25': u'Indre (36)',
        '26': u'Indre-et-Loire (37)',
        '98': u'Isère (38)',
        '41': u'Jura (39)',
        '38': u'La Réunion (974)',
        '5': u'Landes (40)',
        '99': u'Loire (42)',
        '76': u'Loire-Atlantique (44)',
        '28': u'Loiret (45)',
        '27': u'Loir-et-Cher (41)',
        '70': u'Lot (46)',
        '6': u'Lot-et-Garonne (47)',
        '57': u'Lozère (48)',
        '77': u'Maine-et-Loire (49)',
        '13': u'Manche (50)',
        '31': u'Marne (51)',
        '36': u'Martinique (972)',
        '78': u'Mayenne (53)',
        '39': u'Mayotte (976)',
        '62': u'Meurthe-et-Moselle (54)',
        '63': u'Meuse (55)',
        '105': u'Monaco (992)',
        '22': u'Morbihan (56)',
        '64': u'Moselle (57)',
        '16': u'Nièvre (58)',
        '74': u'Nord (59)',
        '109': u'Nouvelle Calédonie  (988)',
        '83': u'Oise (60)',
        '14': u'Orne (61)',
        '46': u'Paris (75)',
        '75': u'Pas-de-Calais (62)',
        '108': u'Polynésie (987)',
        '11': u'Puy-de-Dôme (63)',
        '7': u'Pyrénées-Atlantiques (64)',
        '58': u'Pyrénées-Orientales (66)',
        '100': u'Rhône (69)',
        '17': u'Saône-et-Loire (71)',
        '79': u'Sarthe (72)',
        '101': u'Savoie (73)',
        '47': u'Seine-et-Marne (77)',
        '45': u'Seine-Maritime (76)',
        '51': u'Seine-Saint-Denis (93)',
        '84': u'Somme (80)',
        '107': u'St Pierre et Miquelon (975)',
        '106': u'Suisse (993)',
        '72': u'Tarn (81)',
        '73': u'Tarn-et-Garonne (82)',
        '43': u'Territoire de Belfort (90)',
        '103': u'Tous pays (99)',
        '52': u'Val-de-Marne (94)',
        '53': u'Val-d\'Oise (95)',
        '93': u'Var (83)',
        '94': u'Vaucluse (84)',
        '80': u'Vendée (85)',
        '88': u'Vienne (86)',
        '65': u'Vosges (88)',
        '18': u'Yonne (89)',
        '48': u'Yvelines (78)',
    }.iteritems())])

    Region_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '000000': u'Toutes les régions',
        '1': u'Alsace',
        '2': u'Aquitaine',
        '3': u'Auvergne',
        '4': u'Basse-Normandie',
        '5': u'Bourgogne',
        '6': u'Bretagne',
        '7': u'Centre',
        '8': u'Champagne-Ardenne',
        '9': u'Corse',
        '10': u'DOM TOM',
        '11': u'Franche-Comté',
        '12': u'Haute-Normandie',
        '13': u'île-de-France',
        '14': u'Languedoc-Roussillon',
        '15': u'Limousin',
        '16': u'Lorraine',
        '17': u'Midi-Pyrénées',
        '18': u'Nord-Pas-de-Calais',
        '19': u'Pays de la Loire',
        '20': u'Picardie',
        '21': u'Poitou-Charentes',
        '22': u'Provence-Alpes-Côte d\'Azur',
        '23': u'Rhône-Alpes',
        '24': u'International',
    }.iteritems())])

    JobCategory_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '000000': u'Toutes catégories',
        '1': u'Accueil',
        '4': u'Achats ',
        '32': u'Aéronautique - Navale',
        '9': u'Agriculture - Viticulture - Pêche ',
        '33': u'Agroalimentaire',
        '15': u'Architecture - Immobilier ',
        '13': u'Assurance',
        '41': u'Autres  ',
        '57': u'Autres',
        '60': u'Autres',
        '3': u'Autres Fonctions Administratives',
        '11': u'Banque - Finance ',
        '14': u'Bâtiment - Travaux Publics',
        '58': u'Chimie - Pétrochimie',
        '20': u'Commerce - Vente',
        '59': u'Commerce Appareillage',
        '42': u'Conduite de véhicule',
        '8': u'Direction Générale',
        '37': u'Direction informatique encadrement',
        '53': u'Direction, Encadrement',
        '50': u'Directions, Cadres et Enseignement',
        '28': u'Electricité - Electronique - Automatisme',
        '22': u'Environnement - HSE - Développement durable',
        '10': u'Espaces Verts - Exploitation Forestière',
        '38': u'Etude et développement',
        '43': u'Exploitation de logistique - supply chain',
        '39': u'Exploitation, maintenance et support ',
        '12': u'Gestion - Comptabilité',
        '21': u'Grande et Moyenne Distribution',
        '25': u'Hôtellerie',
        '47': u'Imprimerie - Edition - Arts Graphiques',
        '16': u'Industrie Pharmaceutique / Cosmétologique - Biotech',
        '5': u'Juridique',
        '29': u'Maintenance - Entretien - SAV ',
        '44': u'Manutention',
        '46': u'Marketing - Communication - Medias',
        '30': u'Mécanique Générale',
        '27': u'Métiers de bouche',
        '23': u'Nettoyage - Assainissement - Pressing',
        '34': u'Nucléaire - Production d\'énergie',
        '18': u'Pharmacie Officine / Hospit / Para-pharmacie',
        '35': u'Plasturgie - Bois - Papier - Verre - Cuir - Textile',
        '31': u'Production - Fabrication ',
        '6': u'Qualité',
        '17': u'Recherche Clinique',
        '49': u'Rééducation, Radiologie, Appareillage, LAM',
        '7': u'Ressources Humaines - Formation',
        '26': u'Restauration',
        '2': u'Secrétariat - Assistanat',
        '51': u'Secrétariat, Dentaire, Social, Esthétique et Autres',
        '24': u'Sécurité - Premiers secours',
        '36': u'Sidérurgie - Métallurgie - Tuyauterie - Soudure',
        '48': u'Soignants - Auxiliaires',
        '55': u'Spectacle - Audiovisuel',
        '40': u'Systèmes et réseaux informatique et télécom',
        '52': u'Téléconseil - Télévente - Autres',
        '54': u'Tourisme - Loisirs',
        '45': u'Transport',
        '19': u'Vente, information et promotion du médicament',
        '56': u'Autres',
    }.iteritems())])

    activityDomain_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '000000': u'Tous domaines d\'activité',
        '1': u'Accueil - Secrétariat - Fonctions Administratives',
        '2': u'Achats - Juridique - Qualité - RH - Direction',
        '3': u'Agriculture - Viticulture - Pêche - Espaces Verts',
        '4': u'Automobile',
        '5': u'Banque - Finance - Gestion Comptabilité - Assurance',
        '6': u'Bâtiment - Travaux Publics - Architecture - Immobilier',
        '13': u'Bureaux d\'Etudes - Méthodes',
        '8': u'Commerce - Vente - Grande Distribution',
        '9': u'Environnement - Nettoyage - Sécurité',
        '10': u'Hôtellerie - Restauration - Métiers de Bouche',
        '11': u'Industrie',
        '12': u'Informatique - Technologie de l\'Information',
        '14': u'Logistique - Manutention - Transport',
        '15': u'Marketing - Communication - Imprimerie - Edition',
        '16': u'Médical - Paramédical - Esthétique',
        '7': u'Pharmacie (Industrie, Officine) - Recherche clinique',
        '17': u'Télémarketing - Téléservices',
        '18': u'Tourisme - Loisirs - Spectacle - Audiovisuel',
    }.iteritems())])

    CONFIG = BackendConfig(Value('publication_date', label=u'Publication Date', choices=publicationDate_choices),
                           Value('conty', label=u'County', choices=searchCounty_choices),
                           Value('region', label=u'Region', choices=Region_choices),
                           Value('job_category', label=u'Job Category', choices=JobCategory_choices),
                           Value('activity_domain', label=u'Activity Domain', choices=activityDomain_choices),
                           )

    def search_job(self, pattern=None):
        with self.browser:
            for advert in self.browser.search_job(pattern):
                yield advert

    def advanced_search_job(self):
        for advert in self.browser.advanced_search_job(publication_date=int(self.config['publication_date'].get()),
                                                       conty=int(self.config['conty'].get()),
                                                       region=int(self.config['region'].get()),
                                                       job_category=int(self.config['job_category'].get()),
                                                       activity_domain=int(self.config['activity_domain'].get())
                                                       ):
            yield advert

    def get_job_advert(self, _id, advert=None):
        with self.browser:
            return self.browser.get_job_advert(_id, advert)

    def fill_obj(self, advert, fields):
        self.get_job_advert(advert.id, advert)

    OBJECTS = {AdeccoJobAdvert: fill_obj}
