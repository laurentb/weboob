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
from weboob.tools.value import Value
from .browser import ApecBrowser
from .job import APEC_CONTRATS, APEC_EXPERIENCE

__all__ = ['ApecModule']


class ApecModule(Module, CapJob):
    NAME = 'apec'
    DESCRIPTION = u'apec website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    VERSION = '2.1'

    BROWSER = ApecBrowser

    places_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '001|99700': u'UE Hors France',
        '002|99126': u'..Grèce',
        '003|99132': u'..Royaume Uni',
        '004|99134': u'..Espagne',
        '005|99136': u'..Irlande',
        '006|99139': u'..Portugal',
        '007|99254': u'..Chypre',
        '008|99127': u'..Italie',
        '009|99131': u'..Belgique',
        '010|99135': u'..Pays Bas',
        '011|99137': u'..Luxembourg',
        '012|99144': u'..Malte',
        '013|99145': u'..Slovénie',
        '014|99101': u'..Danemark',
        '015|99104': u'..Suède',
        '016|99105': u'..Finlande',
        '017|99106': u'..Estonie',
        '018|99107': u'..Lettonie',
        '019|99108': u'..Lituanie',
        '020|99109': u'..Allemagne',
        '021|99110': u'..Autriche',
        '022|99111': u'..Bulgarie',
        '023|99112': u'..Hongrie',
        '024|99114': u'..Roumanie',
        '025|99116': u'..République Tchèque',
        '026|99117': u'..Slovaquie',
        '027|99119': u'..Croatie',
        '028|99122': u'..Pologne',
        '029|799': u'France',
        '030|711': u'..Ile-de-France',
        '031|75': u'....Paris',
        '032|77': u'....Seine-et-Marne',
        '033|78': u'....Yvelines',
        '034|91': u'....Essonne',
        '035|92': u'....Hauts-de-Seine',
        '036|93': u'....Seine-Saint-Denis',
        '037|94': u'....Val-de-Marne',
        '038|95': u'....Val-d\'Oise',
        '039|703': u'..Basse-Normandie',
        '040|14': u'....Calvados',
        '041|50': u'....Manche',
        '042|61': u'....Orne',
        '043|705': u'..Bretagne',
        '044|22': u'....Côtes d\'Armor',
        '045|29': u'....Finistère',
        '046|35': u'....Ille-et-Vilaine',
        '047|56': u'....Morbihan',
        '048|706': u'..Centre',
        '049|18': u'....Cher',
        '050|28': u'....Eure-et-Loir',
        '051|36': u'....Indre',
        '052|37': u'....Indre-et-Loire',
        '053|41': u'....Loir-et-Cher',
        '054|45': u'....Loiret',
        '055|710': u'..Haute-Normandie',
        '056|27': u'....Eure',
        '057|76': u'....Seine-Maritime',
        '058|717': u'..Pays de La Loire',
        '059|44': u'....Loire-Atlantique',
        '060|49': u'....Maine-et-Loire',
        '061|53': u'....Mayenne',
        '062|72': u'....Sarthe',
        '063|85': u'....Vendée',
        '064|700': u'..Alsace',
        '065|67': u'....Bas-Rhin',
        '066|68': u'....Haut-Rhin',
        '067|704': u'..Bourgogne',
        '068|21': u'....Côte d\'Or',
        '069|58': u'....Nièvre',
        '070|71': u'....Saône-et-Loire',
        '071|89': u'....Yonne',
        '072|707': u'..Champagne',
        '073|8': u'....Ardennes',
        '074|10': u'....Aube',
        '075|51': u'....Marne',
        '076|52': u'....Haute-Marne',
        '077|709': u'..Franche-Comté',
        '078|25': u'....Doubs',
        '079|39': u'....Jura',
        '080|70': u'....Haute-Saône',
        '081|90': u'....Territoire de Belfort',
        '082|714': u'..Lorraine',
        '083|54': u'....Meurthe-et-Moselle',
        '084|55': u'....Meuse',
        '085|57': u'....Moselle',
        '086|88': u'....Vosges',
        '087|716': u'..Nord-Pas-de-Calais',
        '088|59': u'....Nord',
        '089|62': u'....Pas-de-Calais',
        '090|718': u'..Picardie',
        '091|2': u'....Aisne',
        '092|60': u'....Oise',
        '093|80': u'....Somme',
        '094|20': u'..Corse',
        '095|750': u'....Corse du Sud',
        '096|751': u'....Haute-Corse',
        '097|702': u'..Auvergne',
        '098|3': u'....Allier',
        '099|15': u'....Cantal',
        '100|43': u'....Haute-Loire',
        '101|63': u'....Puy-de-Dôme',
        '102|720': u'..PACA',
        '103|4': u'....Alpes-de-Haute-Provence',
        '104|5': u'....Hautes-Alpes',
        '105|6': u'....Alpes-Maritimes',
        '106|13': u'....Bouches-du-Rhône',
        '107|83': u'....Var',
        '108|84': u'....Vaucluse',
        '109|721': u'..Rhône-Alpes',
        '110|1': u'....Ain',
        '111|7': u'....Ardèche',
        '112|26': u'....Drôme',
        '113|38': u'....Isère',
        '114|42': u'....Loire',
        '115|69': u'....Rhône',
        '116|73': u'....Savoie',
        '117|74': u'....Haute-Savoie',
        '118|701': u'..Aquitaine',
        '119|24': u'....Dordogne',
        '120|33': u'....Gironde',
        '121|40': u'....Landes',
        '122|47': u'....Lot-et-Garonne',
        '123|64': u'....Pyrénées-Atlantiques',
        '124|712': u'..Languedoc-Roussillon',
        '125|11': u'....Aude',
        '126|30': u'....Gard',
        '127|34': u'....Hérault',
        '128|48': u'....Lozère',
        '129|66': u'....Pyrénées-Orientales',
        '130|713': u'..Limousin',
        '131|19': u'....Corrèze',
        '132|23': u'....Creuse',
        '133|87': u'....Haute-Vienne',
        '134|715': u'..Midi-Pyrénées',
        '135|9': u'....Ariège',
        '136|12': u'....Aveyron',
        '137|31': u'....Haute-Garonne',
        '138|32': u'....Gers',
        '139|46': u'....Lot',
        '140|65': u'....Hautes-Pyrénées',
        '141|81': u'....Tarn',
        '142|82': u'....Tarn-et-Garonne',
        '143|719': u'..Poitou-Charentes',
        '144|16': u'....Charente',
        '145|17': u'....Charente-Maritime',
        '146|79': u'....Deux-Sèvres',
        '147|86': u'....Vienne',
        '148|99712': u'..France Outre-Mer',
        '149|99519': u'....Terres Australes et Antarctiques Françaises',
        '150|97100': u'....Guadeloupe',
        '151|97200': u'....Martinique',
        '152|97300': u'....Guyane',
        '153|97400': u'....La Réunion',
        '154|97500': u'....Saint-Pierre-et-Miquelon',
        '155|97600': u'....Mayotte',
        '156|98300': u'....Polynésie Française',
        '157|98600': u'....Wallis et Futuna',
        '158|98800': u'....Nouvelle Calédonie',
        '159|97800': u'....Saint-Martin',
        '160|97700': u'....Saint-Barthélémy',
        '161|102099': u'International',
        '162|99715': u'..Afrique',
        '163|99716': u'..Asie',
        '164|99700': u'..UE Hors France',
        '165|99701': u'..Europe Hors UE',
        '166|99702': u'..Amérique du Nord',
        '167|99711': u'..Océanie',
        '168|99714': u'..Amérique Latine',
    }.items())])

    fonction_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '00|': u'-- Indifférent --',
        '01|101828': u'Commercial, Marketing',
        '02|101782': u'.....Administration des ventes et SAV',
        '03|101783': u'.....Chargé d\'affaires, technico-commercial',
        '04|101784': u'.....Commercial',
        '05|101785': u'.....Commerce international',
        '06|101786': u'.....Direction commerciale et marketing',
        '07|101787': u'.....Direction régionale et d\'agence',
        '08|101788': u'.....Marketing',
        '09|101789': u'.....Ventes en magasin',
        '10|101829': u'Communication, Création',
        '11|101790': u'.....Communication',
        '12|101791': u'.....Création',
        '13|101792': u'.....Documentation, rédaction technique',
        '14|101793': u'.....Journalisme, édition',
        '15|101830': u'Direction d\'entreprise',
        '16|101794': u'.....Adjoint, conseil de direction',
        '17|101795': u'.....Direction générale',
        '18|101831': u'Etudes, Recherche et Développement',
        '19|101796': u'.....Conception, recherche',
        '20|101797': u'.....Direction recherche et développement',
        '21|101798': u'.....Etudes socio-économiques',
        '22|101799': u'.....Projets scientifiques et techniques',
        '23|101800': u'.....Test, essai, validation, expertise',
        '24|101832': u'Gestion, Finance, Administration',
        '25|101801': u'.....Administration, gestion, organisation',
        '26|101802': u'.....Comptabilité',
        '27|101803': u'.....Contrôle de gestion, audit',
        '28|101804': u'.....Direction gestion, finance',
        '29|101805': u'.....Droit, fiscalité',
        '30|101806': u'.....Finance, trésorerie',
        '31|101833': u'Informatique',
        '32|101807': u'.....Direction informatique',
        '33|101808': u'.....Exploitation, maintenance informatique',
        '34|101809': u'.....Informatique de gestion',
        '35|101810': u'.....Informatique industrielle',
        '36|101811': u'.....Informatique web, sites et portails Internet',
        '37|101812': u'.....Maîtrise d\'ouvrage et fonctionnel',
        '38|101813': u'.....Système, réseaux, données',
        '39|101834': u'Production Industrielle, Travaux, Chantiers',
        '40|101814': u'.....Cadres de chantier',
        '41|101815': u'.....Cadres de production industrielle',
        '42|101816': u'.....Direction d\'unité industrielle',
        '43|101835': u'Ressources Humaines',
        '44|101817': u'.....Administration des RH',
        '45|101818': u'.....Développement des RH',
        '46|101819': u'.....Direction des ressources humaines',
        '47|101820': u'.....Formation initiale et continue',
        '48|101836': u'Sanitaire, Social, Culture',
        '49|101821': u'.....Activités sanitaires, sociales et culturelles',
        '50|101837': u'Services Techniques',
        '51|101822': u'.....Achats',
        '52|101823': u'.....Direction des services techniques',
        '53|101824': u'.....Logistique',
        '54|101825': u'.....Maintenance, sécurité',
        '55|101826': u'.....Process, méthodes',
        '56|101827': u'.....Qualité',
    }.items())])

    secteur_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        ' ': u'-- Indifférent --',
        '101752': u'Activités des organisations associatives et administration publique',
        '101753': u'Activités informatiques',
        '101754': u'Activités juridiques et comptables',
        '101755': u'Agroalimentaire',
        '101756': u'Automobile, aéronautique et autres matériels de transport',
        '101757': u'Banque et Assurances',
        '101758': u'Bois - Papier - Imprimerie',
        '101759': u'Chimie - Caoutchouc - Plastique',
        '101760': u'Commerce interentreprises',
        '101761': u'Communication et médias',
        '101762': u'Conseil et gestion des entreprises',
        '101763': u'Construction',
        '101764': u'Distribution généraliste et spécialisée',
        '101765': u'Energies - Eau',
        '101766': u'Equipements électriques et électroniques',
        '101767': u'Formation initiale et continue',
        '101768': u'Gestion des déchets',
        '101769': u'Hôtellerie - Restauration - Loisirs',
        '101770': u'Immobilier',
        '101771': u'Industrie pharmaceutique',
        '101772': u'Ingénierie - R et D',
        '101773': u'Intermédiaires du recrutement',
        '101774': u'Mécanique - Métallurgie',
        '101775': u'Meuble, Textile et autres industries manufacturières',
        '101776': u'Santé - action sociale',
        '101777': u'Services divers aux entreprises',
        '101778': u'Télécommunications',
        '101779': u'Transports et logistique',
    }.items())])

    type_contrat_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted(APEC_CONTRATS.items())])

    salary_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        ' ': u'-- Indifférent --',
        '0|35': u'Moins de 35 K€',
        '35|50': u'Entre 35 et 49 K€',
        '50|70': u'Entre 50 et 69 K€',
        '70|90': u'Entre 70 et 90 K€',
        '90|1000': u'Plus de 90 K€',
    }.items())])

    date_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        ' ': u'-- Indifférent --',
        '101850': u'Aujourd\'hui',
        '101851': u'Les 7 derniers jours',
        '101852': u'Les 30 derniers jours',
        '101853': u'Toutes les offres',
    }.items())])

    level_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted(APEC_EXPERIENCE.items())])

    CONFIG = BackendConfig(Value('place', label=u'Lieu', choices=places_choices, default=''),
                           Value('fonction', label=u'Fonction', choices=fonction_choices, default=''),
                           Value('secteur', label=u'Secteur', choices=secteur_choices, default=''),
                           Value('contrat', label=u'Contrat', choices=type_contrat_choices, default=''),
                           Value('salaire', label=u'Salaire', choices=salary_choices, default=''),
                           Value('limit_date', label=u'Date', choices=date_choices, default=''),
                           Value('level', label=u'Expérience', choices=level_choices, default=''))

    def search_job(self, pattern=None):
        for job_advert in self.browser.search_job(pattern=pattern):
            yield self.fill_obj(job_advert)

    def decode_choice(self, choice):
        splitted_choice = choice.split('|')
        if len(splitted_choice) == 2:
            return splitted_choice[1]
        else:
            return ''

    def advanced_search_job(self):
        for job_advert in self.browser.advanced_search_job(region=self.decode_choice(self.config['place'].get()),
                                                           fonction=self.decode_choice(self.config['fonction'].get()),
                                                           secteur=self.config['secteur'].get(),
                                                           salaire=self.config['salaire'].get(),
                                                           contrat=self.config['contrat'].get(),
                                                           limit_date=self.config['limit_date'].get(),
                                                           level=self.config['level'].get()):
            yield self.fill_obj(job_advert)

    def get_job_advert(self, _id, advert=None):
        job_advert = self.browser.get_job_advert(_id, advert)
        return self.fill_obj(job_advert)

    def fill_obj(self, advert, fields=None):
        if advert.contract_type in self.type_contrat_choices:
            advert.contract_type = self.type_contrat_choices[advert.contract_type]

        if advert.experience in self.level_choices:
            advert.experience = self.level_choices[advert.experience]

        return advert

    OBJECTS = {BaseJobAdvert: fill_obj}
