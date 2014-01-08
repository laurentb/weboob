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
    VERSION = '0.i'

    BROWSER = PopolemploiBrowser

    places_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '100|FRANCE|FRANCE': u'France entière',
        '102|REGION|checkbox': u'Alsace',
        '103|DEPARTEMENT|checkbox_66': u'-- Rhin (Bas) (67)',
        '104|DEPARTEMENT|checkbox_67': u'-- Rhin (Haut) (68)',
        '105|REGION|checkbox_0': u'Aquitaine',
        '106|DEPARTEMENT|checkbox_21': u'-- Dordogne (24)',
        '107|DEPARTEMENT|checkbox_32': u'-- Gironde (33)',
        '108|DEPARTEMENT|checkbox_39': u'-- Landes (40)',
        '109|DEPARTEMENT|checkbox_46': u'-- Lot et Garonne (47)',
        '110|DEPARTEMENT|checkbox_63': u'-- Pyrénées Atlantiques (64)',
        '111|REGION|checkbox_1': u'Auvergne',
        '112|DEPARTEMENT|checkbox_1': u'-- Allier (03)',
        '113|DEPARTEMENT|checkbox_13': u'-- Cantal (15)',
        '114|DEPARTEMENT|checkbox_42': u'-- Loire (Haute) (43)',
        '115|DEPARTEMENT|checkbox_62': u'-- Puy de Dôme (63)',
        '116|REGION|checkbox_2': u'Bourgogne',
        '117|DEPARTEMENT|checkbox_18': u'-- Côte d\'Or (21)',
        '118|DEPARTEMENT|checkbox_57': u'-- Nièvre (58)',
        '119|DEPARTEMENT|checkbox_70': u'-- Saône et Loire (71)',
        '120|DEPARTEMENT|checkbox_88': u'-- Yonne (89)',
        '121|REGION|checkbox_3': u'Bretagne',
        '122|DEPARTEMENT|checkbox_19': u'-- Côtes d\'Armor (22)',
        '123|DEPARTEMENT|checkbox_26': u'-- Finistère (29)',
        '124|DEPARTEMENT|checkbox_34': u'-- Ille et Vilaine (35)',
        '125|DEPARTEMENT|checkbox_54': u'-- Morbihan (56)',
        '126|REGION|checkbox_4': u'Centre',
        '127|DEPARTEMENT|checkbox_16': u'-- Cher (18)',
        '128|DEPARTEMENT|checkbox_25': u'-- Eure et Loir (28)',
        '129|DEPARTEMENT|checkbox_35': u'-- Indre (36)',
        '130|DEPARTEMENT|checkbox_36': u'-- Indre et Loire (37)',
        '131|DEPARTEMENT|checkbox_40': u'-- Loir et Cher (41)',
        '132|DEPARTEMENT|checkbox_44': u'-- Loiret (45)',
        '133|REGION|checkbox_5': u'Champagne Ardenne',
        '134|DEPARTEMENT|checkbox_6': u'-- Ardennes (08)',
        '135|DEPARTEMENT|checkbox_8': u'-- Aube (10)',
        '136|DEPARTEMENT|checkbox_50': u'-- Marne (51)',
        '137|DEPARTEMENT|checkbox_51': u'-- Marne (Haute) (52)',
        '138|REGION|checkbox_6': u'Corse',
        '139|DEPARTEMENT|checkbox_26': u'-- Corse du Sud (2A)',
        '140|DEPARTEMENT|checkbox_27': u'-- Haute Corse (2B)',
        '141|REGION|checkbox_7': u'Franche Comté',
        '142|DEPARTEMENT|checkbox_89': u'-- Belfort (Territoire de) (90)',
        '143|DEPARTEMENT|checkbox_22': u'-- Doubs (25)',
        '144|DEPARTEMENT|checkbox_38': u'-- Jura (39)',
        '145|DEPARTEMENT|checkbox_69': u'-- Saône (Haute) (70)',
        '146|REGION|checkbox_8': u'Ile de France',
        '147|DEPARTEMENT|checkbox_90': u'-- Essonne (91)',
        '148|DEPARTEMENT|checkbox_91': u'-- Hauts de Seine (92)',
        '149|DEPARTEMENT|checkbox_74': u'-- Paris (Dept.) (75)',
        '150|DEPARTEMENT|checkbox_92': u'-- Seine Saint Denis (93)',
        '151|DEPARTEMENT|checkbox_76': u'-- Seine et Marne (77)',
        '152|DEPARTEMENT|checkbox_94': u'-- Val d\'Oise (95)',
        '153|DEPARTEMENT|checkbox_93': u'-- Val de Marne (94)',
        '154|DEPARTEMENT|checkbox_77': u'-- Yvelines (78)',
        '155|REGION|checkbox_9': u'Languedoc Roussillon',
        '156|DEPARTEMENT|checkbox_9': u'-- Aude (11)',
        '157|DEPARTEMENT|checkbox_39': u'-- Gard (30)',
        '158|DEPARTEMENT|checkbox_33': u'-- Hérault (34)',
        '159|DEPARTEMENT|checkbox_47': u'-- Lozère (48)',
        '161|DEPARTEMENT|checkbox_65': u'-- Pyrénées Orientales (66)',
        '162|REGION|checkbox_10': u'Limousin',
        '163|DEPARTEMENT|checkbox_17': u'-- Corrèze (19)',
        '164|DEPARTEMENT|checkbox_20': u'-- Creuse (23)',
        '165|DEPARTEMENT|checkbox_86': u'-- Vienne (Haute) (87)',
        '166|REGION|checkbox_11': u'Lorraine',
        '167|DEPARTEMENT|checkbox_53': u'-- Meurthe et Moselle (54)',
        '168|DEPARTEMENT|checkbox_54': u'-- Meuse (55)',
        '169|DEPARTEMENT|checkbox_56': u'-- Moselle (57)',
        '170|DEPARTEMENT|checkbox_87': u'-- Vosges (88)',
        '171|REGION|checkbox_12': u'Midi Pyrénées',
        '172|DEPARTEMENT|checkbox_7': u'-- Ariège (09)',
        '173|DEPARTEMENT|checkbox_10': u'-- Aveyron (12)',
        '174|DEPARTEMENT|checkbox_30': u'-- Garonne (Haute) (31)',
        '175|DEPARTEMENT|checkbox_31': u'-- Gers (32)',
        '176|DEPARTEMENT|checkbox_45': u'-- Lot (46)',
        '177|DEPARTEMENT|checkbox_64': u'-- Pyrénées (Hautes) (65)',
        '178|DEPARTEMENT|checkbox_80': u'-- Tarn (81)',
        '179|DEPARTEMENT|checkbox_81': u'-- Tarn et Garonne (82)',
        '180|REGION|checkbox_13': u'Nord Pas de Calais',
        '181|DEPARTEMENT|checkbox_58': u'-- Nord (59)',
        '182|DEPARTEMENT|checkbox_61': u'-- Pas de Calais (62)',
        '183|REGION|checkbox_14': u'Normandie (Basse)',
        '184|DEPARTEMENT|checkbox_12': u'-- Calvados (14)',
        '185|DEPARTEMENT|checkbox_49': u'-- Manche (50)',
        '186|DEPARTEMENT|checkbox_60': u'-- Orne (61)',
        '187|REGION|checkbox_15': u'Normandie (Haute)',
        '188|DEPARTEMENT|checkbox_24': u'-- Eure (27)',
        '189|DEPARTEMENT|checkbox_75': u'-- Seine Maritime (76)',
        '190|REGION|checkbox_16': u'Pays de la Loire',
        '191|DEPARTEMENT|checkbox_43': u'-- Loire Atlantique (44)',
        '192|DEPARTEMENT|checkbox_48': u'-- Maine et Loire (49)',
        '193|DEPARTEMENT|checkbox_52': u'-- Mayenne (53)',
        '194|DEPARTEMENT|checkbox_71': u'-- Sarthe (72)',
        '195|DEPARTEMENT|checkbox_84': u'-- Vendée (85)',
        '196|REGION|checkbox_17': u'Picardie',
        '197|DEPARTEMENT|checkbox_0': u'-- Aisne (02)',
        '198|DEPARTEMENT|checkbox_59': u'-- Oise (60)',
        '199|DEPARTEMENT|checkbox_79': u'-- Somme (80)',
        '200|REGION|checkbox_18': u'Poitou Charentes',
        '201|DEPARTEMENT|checkbox_14': u'-- Charente (16)',
        '202|DEPARTEMENT|checkbox_15': u'-- Charente Maritime (17)',
        '203|DEPARTEMENT|checkbox_78': u'-- Sèvres (Deux) (79)',
        '204|DEPARTEMENT|checkbox_85': u'-- Vienne (86)',
        '205|REGION|checkbox_19': u'Provence Alpes Côte d\'Azur',
        '206|DEPARTEMENT|checkbox_3': u'-- Alpes (Hautes) (05)',
        '207|DEPARTEMENT|checkbox_4': u'-- Alpes Maritimes (06)',
        '208|DEPARTEMENT|checkbox_2': u'-- Alpes de Haute Provence (04)',
        '209|DEPARTEMENT|checkbox_13': u'-- Bouches du Rhône (13)',
        '210|DEPARTEMENT|checkbox_82': u'-- Var (83)',
        '211|DEPARTEMENT|checkbox_83': u'-- Vaucluse (84)',
        '212|REGION|checkbox_20': u'Rhône Alpes',
        '213|DEPARTEMENT|checkbox': u'-- Ain (01)',
        '214|DEPARTEMENT|checkbox_5': u'-- Ardèche (07)',
        '215|DEPARTEMENT|checkbox_23': u'-- Drôme (26)',
        '216|DEPARTEMENT|checkbox_37': u'-- Isère (38)',
        '217|DEPARTEMENT|checkbox_41': u'-- Loire (42)',
        '218|DEPARTEMENT|checkbox_68': u'-- Rhône (69)',
        '219|DEPARTEMENT|checkbox_72': u'-- Savoie (73)',
        '220|DEPARTEMENT|checkbox_73': u'-- Savoie (Haute) (74)',
        '221|REGION|checkbox_21': u'Région Antilles / Guyane',
        '222|DEPARTEMENT|checkbox_95': u'-- Guadeloupe (971)',
        '223|DEPARTEMENT|checkbox_97': u'-- Guyane (973)',
        '224|DEPARTEMENT|checkbox_96': u'-- Martinique (972)',
        '225|DEPARTEMENT|checkbox_101': u'-- Saint Barthélémy (977)',
        '226|DEPARTEMENT|checkbox_102': u'-- Saint Martin (978)',
        '227|REGION|checkbox_22': u'Région Atlantique Nord',
        '228|DEPARTEMENT|checkbox_99': u'-- Saint Pierre et Miquelon (975)',
        '229|REGION|checkbox_23': u'Région Pacifique',
        '230|DEPARTEMENT|checkbox_107': u'-- Ile de Clipperton (989)',
        '231|DEPARTEMENT|checkbox_106': u'-- Nouvelle Calédonie (988)',
        '232|DEPARTEMENT|checkbox_105': u'-- Polynésie française (987)',
        '233|DEPARTEMENT|checkbox_103': u'-- Terres australes/antarctiques (984)',
        '234|DEPARTEMENT|checkbox_104': u'-- Wallis et Futuna (986)',
        '235|REGION|checkbox_24': u'Région Réunion / Mayotte',
        '236|DEPARTEMENT|checkbox_100': u'-- Mayotte (976)',
        '237|DEPARTEMENT|checkbox_98': u'-- Réunion (974)',
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

    salary_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        ' ': u'Tout salaire annuel',
        'FOURCHETTE1': u'Moins de 15000',
        'FOURCHETTE2': u'Compris entre 15000 et 18000',
        'FOURCHETTE3': u'Compris entre 18000 et 21000',
        'FOURCHETTE4': u'Compris entre 21000 et 24000',
        'FOURCHETTE5': u'Compris entre 24000 et 36000',
        'FOURCHETTE6': u'Compris entre 36000 et 60000',
        'FOURCHETTE7': u'Supérieur à 60000',
    }.iteritems())])

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
    }.iteritems())])

    limit_date_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '': u'Aucune limite',
        'UN_JOUR': u'Hier',
        'TROIS_JOUR': u'3 jours',
        'UNE_SEMAINE': u'1 semaine',
        'DEUX_SEMAINES': u'2 semaines',
        'UN_MOIS': u'1 mois',
        'TROIS_MOIS': u'3 mois',
    }.iteritems())])

    domain_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        ' ': u'Tout secteur d\'activité',
        '88': u'Action sociale sans hebergt',
        '82': u'Activ.admin/soutien entreprise',
        '66': u'Activ. auxiliaire finance/assu',
        '90': u'Activ. crea/artistiq/spectacle',
        '77': u'Activ. de loc. et loc.-bail',
        '70': u'Activ. siege soc/conseil gest.',
        '93': u'Activ. sportive/recreat/loisir',
        '69': u'Activite juridique/comptable',
        '94': u'Activite organisations assoc.',
        '86': u'Activite pr la sante humaine',
        '53': u'Activites de poste/courrier',
        '64': u'Activite services financiers',
        '68': u'Activites immobilieres',
        '62': u'Activites informatiques',
        '78': u'Activites liees a l\'emploi',
        '75': u'Activites veterinaires',
        '84': u'Administration publiq/defense',
        '79': u'Agences  voyage/activ. liees',
        '71': u'Archi/ing/control/analyse tech',
        '65': u'Assurance',
        '32': u'Autre industrie manufacturiere',
        '74': u'Autres activ.spe scientif/tech',
        '08': u'Autres industries extractives',
        '91': u'Biblio/ musée/ activ. culturel',
        '36': u'Captage/traitement/distrib.eau',
        '19': u'Cokefaction et raffinage',
        '37': u'Collecte/traitement eaux usees',
        '38': u'Collecte/traitnt/elimin dechet',
        '45': u'Commerce/reparation  auto/moto',
        '47': u'Commerce detail sauf auto/moto',
        '46': u'Commerce gros sauf auto/moto',
        '41': u'Construction de batiments',
        '01': u'Cult./prod. animale, chasse',
        '39': u'Depollution/autre gest. dechet',
        '58': u'Edition',
        '80': u'Enquetes et securite',
        '85': u'Enseignement',
        '52': u'Entreposage/sce auxil. transp',
        '06': u'Extraction d\'hydrocarbures',
        '05': u'Extraction houille/ lignite',
        '07': u'Extraction minerais metalliq.',
        '26': u'Fab. prod. info/electro/optiq',
        '22': u'Fabr. prod. caoutchouc/plastiq',
        '30': u'Fabric. autre materiel transp.',
        '23': u'Fabric.autre produit non metal',
        '28': u'Fabric. autres machines/equip.',
        '27': u'Fabric. d\'equip. electriques',
        '31': u'Fabrication de meubles',
        '12': u'Fabrication produit base tabac',
        '25': u'Fabrication produits metalliq',
        '42': u'Genie civil',
        '55': u'Hebergement',
        '87': u'Hebergt médico-social/ social',
        '18': u'Imprimerie/reprod. enregistre.',
        '00': u'Indetermine',
        '29': u'Industrie automobile',
        '20': u'Industrie chimique',
        '14': u'Industrie de l\'habillement',
        '11': u'Industrie des boissons',
        '15': u'Industrie du cuir/la chaussure',
        '17': u'Industrie du papier/du carton',
        '21': u'Industrie pharmaceutique',
        '10': u'Industries alimentaires',
        '13': u'Industrie textile',
        '24': u'Metallurgie',
        '92': u'Orga. jeux  hasard/argent',
        '99': u'Organisations et organismes',
        '03': u'Peche et aquaculture',
        '35': u'Prod./distrib.elec/gaz/vap/air',
        '59': u'Prod film cine/video/tv/musiq',
        '98': u'Production menage bien propre',
        '60': u'Programmation et diffusion',
        '73': u'Publicite et etudes de marche',
        '72': u'Rech.-dev. scientifique',
        '33': u'Repar./instal. machines/equip.',
        '95': u'Repar.pc/biens perso/domestiq',
        '56': u'Restauration',
        '97': u'Sce domestique pr particuliers',
        '81': u'Services bat/amenagnt paysager',
        '63': u'Services d\'information',
        '96': u'Services personnels',
        '09': u'Soutien industries extractives',
        '02': u'Sylvicult./exploit. forestiere',
        '61': u'Telecommunications',
        '51': u'Transports aeriens',
        '50': u'Transports par eau',
        '49': u'Transports terrestres',
        '16': u'Travail bois/fab. article bois',
        '43': u'Travaux constr.specialises',
    }.iteritems())])

    CONFIG = BackendConfig(Value('metier', label='Job name', masked=False, default=''),
                           Value('place', label=u'Place', choices=places_choices, default='100|FRANCE|FRANCE'),
                           Value('contrat', label=u'Contract', choices=type_contrat_choices, default=''),
                           Value('salary', label=u'Salary', choices=salary_choices, default=''),
                           Value('qualification', label=u'Qualification', choices=qualification_choices, default=''),
                           Value('limit_date', label=u'Date limite', choices=limit_date_choices, default=''),
                           Value('domain', label=u'Domain', choices=domain_choices, default=''))

    def search_job(self, pattern=None):
        with self.browser:
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
        with self.browser:
            return self.browser.get_job_advert(_id, advert)

    def fill_obj(self, advert, fields):
        self.get_job_advert(advert.id, advert)

    OBJECTS = {PopolemploiJobAdvert: fill_obj}
