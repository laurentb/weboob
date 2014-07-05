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
from weboob.capabilities.job import CapJob
from .browser import AdeccoBrowser
from .job import AdeccoJobAdvert

__all__ = ['AdeccoBackend']


class AdeccoBackend(BaseBackend, CapJob):
    NAME = 'adecco'
    DESCRIPTION = u'adecco website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    VERSION = '0.j'

    BROWSER = AdeccoBrowser

    publicationDate_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '000000': u'-- Indifférent --',
        '1': u'Moins de 48 heures',
        '2': u'Moins de 1 semaine',
        '4': u'Moins de 2 semaines',
        '3': u'Moins de 5 semaines',
    }.iteritems())])

    type_contract_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '000000': u'--Indifferent--',
        '1': u'CDD',
        '2': u'CDI',
        '3': u'Intérim',
        '4': u'Emploi formation',
        '5': u'Emploi saisonnier',
        '6': u'Stage',
        '7': u'Autre',
    }.iteritems())])

    places_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '100|REGION_0|DEPARTEMENT_0': u'--Indifferent--',
        '101|REGION_1': u'Alsace',
        '102|REGION_1|DEPARTEMENT_1': u'-- Rhin (Bas) (67)',
        '103|REGION_1|DEPARTEMENT_2': u'-- Rhin (Haut) (68)',
        '104|REGION_2': u'Aquitaine',
        '105|REGION_2|DEPARTEMENT_3': u'-- Dordogne (24)',
        '106|REGION_2|DEPARTEMENT_4': u'-- Gironde (33)',
        '107|REGION_2|DEPARTEMENT_5': u'-- Landes (40)',
        '108|REGION_2|DEPARTEMENT_6': u'-- Lot et Garonne (47)',
        '109|REGION_2|DEPARTEMENT_7': u'-- Pyrénées Atlantiques (64)',
        '110|REGION_3': u'Auvergne',
        '111|REGION_3|DEPARTEMENT_8': u'-- Allier (03)',
        '112|REGION_3|DEPARTEMENT_9': u'-- Cantal (15)',
        '113|REGION_3|DEPARTEMENT_10': u'-- Loire (Haute) (43)',
        '114|REGION_3|DEPARTEMENT_11': u'-- Puy de Dôme (63)',
        '115|REGION_5': u'Bourgogne',
        '116|REGION_5|DEPARTEMENT_15': u'-- Côte d\'Or (21)',
        '117|REGION_5|DEPARTEMENT_16': u'-- Nièvre (58)',
        '118|REGION_5|DEPARTEMENT_17': u'-- Saône et Loire (71)',
        '119|REGION_5|DEPARTEMENT_18': u'-- Yonne (89)',
        '120|REGION_6': u'Bretagne',
        '121|REGION_6|DEPARTEMENT_19': u'-- Côtes d\'Armor (22)',
        '122|REGION_6|DEPARTEMENT_20': u'-- Finistère (29)',
        '123|REGION_6|DEPARTEMENT_21': u'-- Ille et Vilaine (35)',
        '124|REGION_6|DEPARTEMENT_22': u'-- Morbihan (56)',
        '125|REGION_7': u'Centre',
        '126|REGION_7|DEPARTEMENT_23': u'-- Cher (18)',
        '127|REGION_7|DEPARTEMENT_24': u'-- Eure et Loir (28)',
        '128|REGION_7|DEPARTEMENT_25': u'-- Indre (36)',
        '129|REGION_7|DEPARTEMENT_26': u'-- Indre et Loire (37)',
        '130|REGION_7|DEPARTEMENT_27': u'-- Loir et Cher (41)',
        '131|REGION_7|DEPARTEMENT_28': u'-- Loiret (45)',
        '132|REGION_8': u'Champagne Ardenne',
        '133|REGION_8|DEPARTEMENT_29': u'-- Ardennes (08)',
        '134|REGION_8|DEPARTEMENT_30': u'-- Aube (10)',
        '135|REGION_8|DEPARTEMENT_31': u'-- Marne (51)',
        '136|REGION_8|DEPARTEMENT_32': u'-- Marne (Haute) (52)',
        '137|REGION_9': u'Corse',
        '138|REGION_9|DEPARTEMENT_33': u'-- Corse du Sud (2A)',
        '139|REGION_9|DEPARTEMENT_34': u'-- Haute Corse (2B)',
        '140|REGION_11': u'Franche Comté',
        '141|REGION_11|DEPARTEMENT_43': u'-- Belfort (Territoire de) (90)',
        '142|REGION_11|DEPARTEMENT_40': u'-- Doubs (25)',
        '143|REGION_11|DEPARTEMENT_41': u'-- Jura (39)',
        '144|REGION_11|DEPARTEMENT_42': u'-- Saône (Haute) (70)',
        '145|REGION_13': u'Ile de France',
        '146|REGION_13|DEPARTEMENT_49': u'-- Essonne (91)',
        '147|REGION_13|DEPARTEMENT_50': u'-- Hauts de Seine (92)',
        '148|REGION_13|DEPARTEMENT_46': u'-- Paris (Dept.) (75)',
        '149|REGION_13|DEPARTEMENT_51': u'-- Seine Saint Denis (93)',
        '150|REGION_13|DEPARTEMENT_47': u'-- Seine et Marne (77)',
        '151|REGION_13|DEPARTEMENT_53': u'-- Val d\'Oise (95)',
        '152|REGION_13|DEPARTEMENT_52': u'-- Val de Marne (94)',
        '153|REGION_13|DEPARTEMENT_48': u'-- Yvelines (78)',
        '154|REGION_14': u'Languedoc Roussillon',
        '155|REGION_14|DEPARTEMENT_54': u'-- Aude (11)',
        '156|REGION_14|DEPARTEMENT_55': u'-- Gard (30)',
        '157|REGION_14|DEPARTEMENT_56': u'-- Hérault (34)',
        '158|REGION_14|DEPARTEMENT_57': u'-- Lozère (48)',
        '159|REGION_14|DEPARTEMENT_58': u'-- Pyrénées Orientales (66)',
        '160|REGION_15': u'Limousin',
        '161|REGION_15|DEPARTEMENT_59': u'-- Corrèze (19)',
        '162|REGION_15|DEPARTEMENT_60': u'-- Creuse (23)',
        '163|REGION_15|DEPARTEMENT_61': u'-- Vienne (Haute) (87)',
        '164|REGION_16': u'Lorraine',
        '165|REGION_16|DEPARTEMENT_62': u'-- Meurthe et Moselle (54)',
        '166|REGION_16|DEPARTEMENT_63': u'-- Meuse (55)',
        '167|REGION_16|DEPARTEMENT_64': u'-- Moselle (57)',
        '168|REGION_16|DEPARTEMENT_65': u'-- Vosges (88)',
        '169|REGION_17': u'Midi Pyrénées',
        '170|REGION_17|DEPARTEMENT_66': u'-- Ariège (09)',
        '171|REGION_17|DEPARTEMENT_67': u'-- Aveyron (12)',
        '172|REGION_17|DEPARTEMENT_68': u'-- Garonne (Haute) (31)',
        '173|REGION_17|DEPARTEMENT_69': u'-- Gers (32)',
        '174|REGION_17|DEPARTEMENT_70': u'-- Lot (46)',
        '175|REGION_17|DEPARTEMENT_71': u'-- Pyrénées (Hautes) (65)',
        '176|REGION_17|DEPARTEMENT_72': u'-- Tarn (81)',
        '177|REGION_17|DEPARTEMENT_73': u'-- Tarn et Garonne (82)',
        '178|REGION_18': u'Nord Pas de Calais',
        '179|REGION_18|DEPARTEMENT_74': u'-- Nord (59)',
        '180|REGION_18|DEPARTEMENT_75': u'-- Pas de Calais (62)',
        '181|REGION_4': u'Normandie (Basse)',
        '182|REGION_4|DEPARTEMENT_12': u'-- Calvados (14)',
        '183|REGION_4|DEPARTEMENT_13': u'-- Manche (50)',
        '184|REGION_4|DEPARTEMENT_14': u'-- Orne (61)',
        '185|REGION_12': u'Normandie (Haute)',
        '186|REGION_12|DEPARTEMENT_44': u'-- Eure (27)',
        '187|REGION_12|DEPARTEMENT_47': u'-- Seine Maritime (76)',
        '188|REGION_19': u'Pays de la Loire',
        '189|REGION_19|DEPARTEMENT_76': u'-- Loire Atlantique (44)',
        '190|REGION_19|DEPARTEMENT_77': u'-- Maine et Loire (49)',
        '191|REGION_19|DEPARTEMENT_78': u'-- Mayenne (53)',
        '192|REGION_19|DEPARTEMENT_79': u'-- Sarthe (72)',
        '193|REGION_19|DEPARTEMENT_80': u'-- Vendée (85)',
        '194|REGION_20': u'Picardie',
        '195|REGION_20|DEPARTEMENT_81': u'-- Aisne (02)',
        '196|REGION_20|DEPARTEMENT_83': u'-- Oise (60)',
        '197|REGION_20|DEPARTEMENT_84': u'-- Somme (80)',
        '198|REGION_21': u'Poitou Charentes',
        '199|REGION_21|DEPARTEMENT_85': u'-- Charente (16)',
        '200|REGION_21|DEPARTEMENT_86': u'-- Charente Maritime (17)',
        '201|REGION_21|DEPARTEMENT_87': u'-- Sèvres (Deux) (79)',
        '202|REGION_21|DEPARTEMENT_88': u'-- Vienne (86)',
        '203|REGION_22': u'Provence Alpes Côte d\'Azur',
        '204|REGION_22|DEPARTEMENT_90': u'-- Alpes (Hautes) (05)',
        '205|REGION_22|DEPARTEMENT_91': u'-- Alpes Maritimes (06)',
        '206|REGION_22|DEPARTEMENT_89': u'-- Alpes de Haute Provence (04)',
        '207|REGION_22|DEPARTEMENT_92': u'-- Bouches du Rhône (13)',
        '208|REGION_22|DEPARTEMENT_93': u'-- Var (83)',
        '209|REGION_22|DEPARTEMENT_94': u'-- Vaucluse (84)',
        '210|REGION_23': u'Rhône Alpes',
        '211|REGION_23|DEPARTEMENT_95': u'-- Ain (01)',
        '212|REGION_23|DEPARTEMENT_96': u'-- Ardèche (07)',
        '213|REGION_23|DEPARTEMENT_97': u'-- Drôme (26)',
        '214|REGION_23|DEPARTEMENT_98': u'-- Isère (38)',
        '215|REGION_23|DEPARTEMENT_99': u'-- Loire (42)',
        '216|REGION_23|DEPARTEMENT_100': u'-- Rhône (69)',
        '217|REGION_23|DEPARTEMENT_101': u'-- Savoie (73)',
        '218|REGION_23|DEPARTEMENT_102': u'-- Savoie (Haute) (74)',
        '219|REGION_10': u'DOM TOM',
        '220|REGION_10|DEPARTEMENT_35': u'-- Guadeloupe (971)',
        '221|REGION_10|DEPARTEMENT_37': u'-- Guyane (973)',
        '222|REGION_10|DEPARTEMENT_38': u'-- La Réunion (974)',
        '223|REGION_10|DEPARTEMENT_36': u'-- Martinique (972)',
        '224|REGION_10|DEPARTEMENT_108': u'-- Mayotte (976)',
        '225|REGION_10|DEPARTEMENT_109': u'-- Nouvelle Calédonie (988)',
        '226|REGION_10|DEPARTEMENT_108': u'-- Polynésie (987)',
        '227|REGION_10|DEPARTEMENT_107': u'-- Saint Pierre et Miquelon (975)',
        '228|REGION_24': u'International',
        '229|REGION_24|DEPARTEMENT_104': u'-- Andorre',
        '230|REGION_24|DEPARTEMENT_105': u'-- Monaco',
        '231|REGION_24|DEPARTEMENT_106': u'-- Suisse',
    }.iteritems())])

    activityDomain_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '100|DOMAIN_0': u'Tous domaines d\'activité',
        '101|DOMAIN_1': u'Accueil - Secrétariat - Fonctions Administratives',
        '102|DOMAIN_1|ACTIVITY_1': u'-- Accueil',
        '103|DOMAIN_1|ACTIVITY_2': u'-- Secrétariat - Assistanat',
        '104|DOMAIN_1|ACTIVITY_3': u'-- Autres Fonctions Administratives',
        '105|DOMAIN_2': u'Achats - Juridique - Qualité - RH - Direction',
        '106|DOMAIN_2|ACTIVITY_4': u'-- Achats ',
        '107|DOMAIN_2|ACTIVITY_5': u'-- Juridique',
        '108|DOMAIN_2|ACTIVITY_6': u'-- Qualité',
        '109|DOMAIN_2|ACTIVITY_7': u'Ressources Humaines - Formation',
        '110|DOMAIN_2|ACTIVITY_8': u'-- Direction Générale',
        '111|DOMAIN_3': u'Agriculture - Viticulture - Pêche - Espaces Verts',
        '112|DOMAIN_3|ACTIVITY_9': u'-- Agriculture - Viticulture - Pêche ',
        '113|DOMAIN_3|ACTIVITY_10': u'-- Espaces Verts - Exploitation Forestière',
        '114|DOMAIN_4': u'Automobile',
        '115|DOMAIN_5': u'Banque - Finance - Gestion Comptabilité - Assurance',
        '116|DOMAIN_5|ACTIVITY_11': u'-- Banque - Finance ',
        '117|DOMAIN_5|ACTIVITY_12': u'-- Gestion - Comptabilité',
        '118|DOMAIN_5|ACTIVITY_13': u'-- Assurance',
        '119|DOMAIN_6': u'Bâtiment - Travaux Publics - Architecture - Immobilier',
        '120|DOMAIN_6|ACTIVITY_14': u'-- Bâtiment - Travaux Publics',
        '121|DOMAIN_6|ACTIVITY_15': u'-- Architecture - Immobilier ',
        '122|DOMAIN_13': u'Bureaux d\'Etudes - Méthodes',
        '123|DOMAIN_8': u'Commerce - Vente - Grande Distribution',
        '124|DOMAIN_8|ACTIVITY_20': u'-- Commerce - Vente',
        '125|DOMAIN_8|ACTIVITY_21': u'-- Grande et Moyenne Distribution',
        '126|DOMAIN_9': u'Environnement - Nettoyage - Sécurité',
        '127|DOMAIN_9|ACTIVITY_22': u'-- Environnement - HSE - Développement durable',
        '128|DOMAIN_9|ACTIVITY_23': u'-- Nettoyage - Assainissement - Pressing',
        '129|DOMAIN_9|ACTIVITY_24': u'-- Sécurité - Premiers secours',
        '130|DOMAIN_10': u'Hôtellerie - Restauration - Métiers de Bouche',
        '131|DOMAIN_10|ACTIVITY_25': u'-- Hôtellerie',
        '132|DOMAIN_10|ACTIVITY_27': u'-- Métiers de bouche',
        '133|DOMAIN_10|ACTIVITY_26': u'-- Restauration',
        '134|DOMAIN_11': u'Industrie',
        '135|DOMAIN_11|ACTIVITY_32': u'-- Aéronautique - Navale',
        '136|DOMAIN_11|ACTIVITY_33': u'-- Agroalimentaire',
        '137|DOMAIN_11|ACTIVITY_58': u'-- Chimie - Pétrochimie',
        '138|DOMAIN_11|ACTIVITY_28': u'-- Electricité - Electronique - Automatisme',
        '139|DOMAIN_11|ACTIVITY_29': u'-- Maintenance - Entretien - SAV ',
        '140|DOMAIN_11|ACTIVITY_30': u'-- Mécanique Générale',
        '141|DOMAIN_11|ACTIVITY_31': u'-- Production - Fabrication ',
        '142|DOMAIN_11|ACTIVITY_36': u'-- Sidérurgie - Métallurgie - Tuyauterie - Soudure',
        '143|DOMAIN_11|ACTIVITY_34': u'-- Nucléaire - Production d\'énergie',
        '144|DOMAIN_11|ACTIVITY_35': u'-- Plasturgie - Bois - Papier - Verre - Cuir - Textile',
        '145|DOMAIN_12': u'Informatique - Technologie de l\'Information',
        '146|DOMAIN_12|ACTIVITY_37': u'-- Direction informatique encadrement',
        '147|DOMAIN_12|ACTIVITY_38': u'-- Etude et développement',
        '148|DOMAIN_12|ACTIVITY_39': u'-- Exploitation, maintenance et support ',
        '149|DOMAIN_12|ACTIVITY_40': u'-- Systèmes et réseaux informatique et télécom',
        '150|DOMAIN_14': u'Logistique - Manutention - Transport',
        '151|DOMAIN_14|ACTIVITY_42': u'-- Conduite de véhicule',
        '152|DOMAIN_14|ACTIVITY_43': u'-- Exploitation de logistique - supply chain',
        '153|DOMAIN_14|ACTIVITY_44': u'-- Manutention',
        '154|DOMAIN_14|ACTIVITY_45': u'-- Transport',
        '155|DOMAIN_15': u'Marketing - Communication - Imprimerie - Edition',
        '156|DOMAIN_15|ACTIVITY_47': u'-- Imprimerie - Edition - Arts Graphiques',
        '157|DOMAIN_15|ACTIVITY_46': u'-- Marketing - Communication - Medias',
        '158|DOMAIN_16': u'Médical - Paramédical - Esthétique',
        '159|DOMAIN_16|ACTIVITY_59': u'-- Commerce Appareillage',
        '160|DOMAIN_16|ACTIVITY_50': u'-- Directions, Cadres et Enseignement',
        '161|DOMAIN_16|ACTIVITY_49': u'-- Rééducation, Radiologie, Appareillage, LAM',
        '162|DOMAIN_16|ACTIVITY_51': u'-- Secrétariat, Dentaire, Social, Esthétique et Autres',
        '163|DOMAIN_16|ACTIVITY_48': u'-- Soignants - Auxiliaires',
        '164|DOMAIN_7': u'Pharmacie (Industrie, Officine) - Recherche clinique',
        '165|DOMAIN_7|ACTIVITY_16': u'-- Industrie Pharmaceutique / Cosmétologique - Biotech',
        '166|DOMAIN_7|ACTIVITY_17': u'-- Recherche Clinique',
        '167|DOMAIN_7|ACTIVITY_18': u'-- Pharmacie Officine / Hospit / Para-pharmacie',
        '168|DOMAIN_7|ACTIVITY_19': u'-- Vente, information et promotion du médicament',
        '169|DOMAIN_17': u'Télémarketing - Téléservices',
        '170|DOMAIN_17|ACTIVITY_52': u'-- Téléconseil - Télévente - Autres',
        '171|DOMAIN_17|ACTIVITY_53': u'-- Direction, Encadrement',
        '172|DOMAIN_18': u'Tourisme - Loisirs - Spectacle - Audiovisuel',
        '173|DOMAIN_18|ACTIVITY_54': u'-- Tourisme - Loisirs',
        '174|DOMAIN_18|ACTIVITY_55': u'-- Spectacle - Audiovisuel',
    }.iteritems())])

    CONFIG = BackendConfig(Value('publication_date', label=u'Publication Date', choices=publicationDate_choices),
                           Value('place', label=u'Place', choices=places_choices),
                           Value('contract', labe=u'Contract type', choices=type_contract_choices),
                           Value('activity_domain', label=u'Activity Domain', choices=activityDomain_choices),
                           )

    def search_job(self, pattern=None):
        with self.browser:
            for advert in self.browser.search_job(pattern):
                yield advert

    def decode_choice(self, place):
        splitted_choice = place.split('|')
        part1 = splitted_choice[1].split('_')[1]
        if len(splitted_choice) == 3:
            part2 = splitted_choice[2].split('_')[1]
            return part1, part2
        else:
            return part1, 0

    def advanced_search_job(self):
        region, departement = self.decode_choice(self.config['place'].get())
        domain, category = self.decode_choice(self.config['activity_domain'].get())
        for advert in self.browser.advanced_search_job(publication_date=int(self.config['publication_date'].get()),
                                                       contract_type=int(self.config['contract'].get()),
                                                       conty=departement,
                                                       region=region,
                                                       job_category=category,
                                                       activity_domain=domain
                                                       ):
            yield advert

    def get_job_advert(self, _id, advert=None):
        with self.browser:
            return self.browser.get_job_advert(_id, advert)

    def fill_obj(self, advert, fields):
        self.get_job_advert(advert.id, advert)

    OBJECTS = {AdeccoJobAdvert: fill_obj}
