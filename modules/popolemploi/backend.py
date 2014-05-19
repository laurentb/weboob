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
    VERSION = '0.j'

    BROWSER = PopolemploiBrowser

    places_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '100|FRANCE|O1': u'France entière',
        '102|REGION|42': u'Alsace',
        '103|DEPARTEMENT|67': u'-- Rhin (Bas) (67)',
        '104|DEPARTEMENT|68': u'-- Rhin (Haut) (68)',
        '105|REGION|72': u'Aquitaine',
        '106|DEPARTEMENT|24': u'-- Dordogne (24)',
        '107|DEPARTEMENT|33': u'-- Gironde (33)',
        '108|DEPARTEMENT|40': u'-- Landes (40)',
        '109|DEPARTEMENT|47': u'-- Lot et Garonne (47)',
        '110|DEPARTEMENT|64': u'-- Pyrénées Atlantiques (64)',
        '111|REGION|83': u'Auvergne',
        '112|DEPARTEMENT|03': u'-- Allier (03)',
        '113|DEPARTEMENT|15': u'-- Cantal (15)',
        '114|DEPARTEMENT|43': u'-- Loire (Haute) (43)',
        '115|DEPARTEMENT|63': u'-- Puy de Dôme (63)',
        '116|REGION|26': u'Bourgogne',
        '117|DEPARTEMENT|21': u'-- Côte d\'Or (21)',
        '118|DEPARTEMENT|58': u'-- Nièvre (58)',
        '119|DEPARTEMENT|71': u'-- Saône et Loire (71)',
        '120|DEPARTEMENT|89': u'-- Yonne (89)',
        '121|REGION|53': u'Bretagne',
        '122|DEPARTEMENT|22': u'-- Côtes d\'Armor (22)',
        '123|DEPARTEMENT|29': u'-- Finistère (29)',
        '124|DEPARTEMENT|35': u'-- Ille et Vilaine (35)',
        '125|DEPARTEMENT|56': u'-- Morbihan (56)',
        '126|REGION|24': u'Centre',
        '127|DEPARTEMENT|18': u'-- Cher (18)',
        '128|DEPARTEMENT|28': u'-- Eure et Loir (28)',
        '129|DEPARTEMENT|36': u'-- Indre (36)',
        '130|DEPARTEMENT|37': u'-- Indre et Loire (37)',
        '131|DEPARTEMENT|41': u'-- Loir et Cher (41)',
        '132|DEPARTEMENT|45': u'-- Loiret (45)',
        '133|REGION|21': u'Champagne Ardenne',
        '134|DEPARTEMENT|08': u'-- Ardennes (08)',
        '135|DEPARTEMENT|10': u'-- Aube (10)',
        '136|DEPARTEMENT|51': u'-- Marne (51)',
        '137|DEPARTEMENT|52': u'-- Marne (Haute) (52)',
        '138|REGION|94': u'Corse',
        '139|DEPARTEMENT|2A': u'-- Corse du Sud (2A)',
        '140|DEPARTEMENT|2B': u'-- Haute Corse (2B)',
        '141|REGION|43': u'Franche Comté',
        '142|DEPARTEMENT|90': u'-- Belfort (Territoire de) (90)',
        '143|DEPARTEMENT|25': u'-- Doubs (25)',
        '144|DEPARTEMENT|39': u'-- Jura (39)',
        '145|DEPARTEMENT|70': u'-- Saône (Haute) (70)',
        '146|REGION|11': u'Ile de France',
        '147|DEPARTEMENT|91': u'-- Essonne (91)',
        '148|DEPARTEMENT|92': u'-- Hauts de Seine (92)',
        '149|DEPARTEMENT|75': u'-- Paris (Dept.) (75)',
        '150|DEPARTEMENT|93': u'-- Seine Saint Denis (93)',
        '151|DEPARTEMENT|77': u'-- Seine et Marne (77)',
        '152|DEPARTEMENT|95': u'-- Val d\'Oise (95)',
        '153|DEPARTEMENT|94': u'-- Val de Marne (94)',
        '154|DEPARTEMENT|78': u'-- Yvelines (78)',
        '155|REGION|91': u'Languedoc Roussillon',
        '156|DEPARTEMENT|11': u'-- Aude (11)',
        '157|DEPARTEMENT|30': u'-- Gard (30)',
        '158|DEPARTEMENT|34': u'-- Hérault (34)',
        '159|DEPARTEMENT|48': u'-- Lozère (48)',
        '161|DEPARTEMENT|66': u'-- Pyrénées Orientales (66)',
        '162|REGION|74': u'Limousin',
        '163|DEPARTEMENT|19': u'-- Corrèze (19)',
        '164|DEPARTEMENT|23': u'-- Creuse (23)',
        '165|DEPARTEMENT|87': u'-- Vienne (Haute) (87)',
        '166|REGION|41': u'Lorraine',
        '167|DEPARTEMENT|54': u'-- Meurthe et Moselle (54)',
        '168|DEPARTEMENT|55': u'-- Meuse (55)',
        '169|DEPARTEMENT|57': u'-- Moselle (57)',
        '170|DEPARTEMENT|88': u'-- Vosges (88)',
        '171|REGION|73': u'Midi Pyrénées',
        '172|DEPARTEMENT|09': u'-- Ariège (09)',
        '173|DEPARTEMENT|12': u'-- Aveyron (12)',
        '174|DEPARTEMENT|31': u'-- Garonne (Haute) (31)',
        '175|DEPARTEMENT|32': u'-- Gers (32)',
        '176|DEPARTEMENT|46': u'-- Lot (46)',
        '177|DEPARTEMENT|65': u'-- Pyrénées (Hautes) (65)',
        '178|DEPARTEMENT|81': u'-- Tarn (81)',
        '179|DEPARTEMENT|82': u'-- Tarn et Garonne (82)',
        '180|REGION|31': u'Nord Pas de Calais',
        '181|DEPARTEMENT|59': u'-- Nord (59)',
        '182|DEPARTEMENT|62': u'-- Pas de Calais (62)',
        '183|REGION|25': u'Normandie (Basse)',
        '184|DEPARTEMENT|14': u'-- Calvados (14)',
        '185|DEPARTEMENT|50': u'-- Manche (50)',
        '186|DEPARTEMENT|61': u'-- Orne (61)',
        '187|REGION|23': u'Normandie (Haute)',
        '188|DEPARTEMENT|27': u'-- Eure (27)',
        '189|DEPARTEMENT|76': u'-- Seine Maritime (76)',
        '190|REGION|52': u'Pays de la Loire',
        '191|DEPARTEMENT|44': u'-- Loire Atlantique (44)',
        '192|DEPARTEMENT|49': u'-- Maine et Loire (49)',
        '193|DEPARTEMENT|53': u'-- Mayenne (53)',
        '194|DEPARTEMENT|72': u'-- Sarthe (72)',
        '195|DEPARTEMENT|85': u'-- Vendée (85)',
        '196|REGION|22': u'Picardie',
        '197|DEPARTEMENT|02': u'-- Aisne (02)',
        '198|DEPARTEMENT|60': u'-- Oise (60)',
        '199|DEPARTEMENT|80': u'-- Somme (80)',
        '200|REGION|54': u'Poitou Charentes',
        '201|DEPARTEMENT|16': u'-- Charente (16)',
        '202|DEPARTEMENT|17': u'-- Charente Maritime (17)',
        '203|DEPARTEMENT|79': u'-- Sèvres (Deux) (79)',
        '204|DEPARTEMENT|86': u'-- Vienne (86)',
        '205|REGION|93': u'Provence Alpes Côte d\'Azur',
        '206|DEPARTEMENT|05': u'-- Alpes (Hautes) (05)',
        '207|DEPARTEMENT|06': u'-- Alpes Maritimes (06)',
        '208|DEPARTEMENT|04': u'-- Alpes de Haute Provence (04)',
        '209|DEPARTEMENT|13': u'-- Bouches du Rhône (13)',
        '210|DEPARTEMENT|83': u'-- Var (83)',
        '211|DEPARTEMENT|84': u'-- Vaucluse (84)',
        '212|REGION|82': u'Rhône Alpes',
        '213|DEPARTEMENT|01': u'-- Ain (01)',
        '214|DEPARTEMENT|07': u'-- Ardèche (07)',
        '215|DEPARTEMENT|26': u'-- Drôme (26)',
        '216|DEPARTEMENT|38': u'-- Isère (38)',
        '217|DEPARTEMENT|42': u'-- Loire (42)',
        '218|DEPARTEMENT|69': u'-- Rhône (69)',
        '219|DEPARTEMENT|73': u'-- Savoie (73)',
        '220|DEPARTEMENT|74': u'-- Savoie (Haute) (74)',
        '221|REGION|03': u'Région Antilles / Guyane',
        '222|DEPARTEMENT|971': u'-- Guadeloupe (971)',
        '223|DEPARTEMENT|973': u'-- Guyane (973)',
        '224|DEPARTEMENT|972': u'-- Martinique (972)',
        '225|DEPARTEMENT|977': u'-- Saint Barthélémy (977)',
        '226|DEPARTEMENT|978': u'-- Saint Martin (978)',
        '227|REGION|98': u'Région Atlantique Nord',
        '228|DEPARTEMENT|975': u'-- Saint Pierre et Miquelon (975)',
        '229|REGION|95': u'Région Pacifique',
        '230|DEPARTEMENT|989': u'-- Ile de Clipperton (989)',
        '231|DEPARTEMENT|988': u'-- Nouvelle Calédonie (988)',
        '232|DEPARTEMENT|987': u'-- Polynésie française (987)',
        '233|DEPARTEMENT|984': u'-- Terres australes/antarctiques (984)',
        '234|DEPARTEMENT|986': u'-- Wallis et Futuna (986)',
        '235|REGION|97': u'Région Réunion / Mayotte',
        '236|DEPARTEMENT|976': u'-- Mayotte (976)',
        '237|DEPARTEMENT|974': u'-- Réunion (974)',
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
        ' ': u'Aucune limite',
        '1': u'Hier',
        '3': u'3 jours',
        '7': u'1 semaine',
        '14': u'2 semaines',
        '31': u'1 mois',
        '93': u'3 mois',
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
                           Value('place', label=u'Place', choices=places_choices, default='100|FRANCE|01'),
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
