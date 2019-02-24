# -*- coding: utf-8 -*-

# Copyright(C) 2016      Bezleputh
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

from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value
from weboob.capabilities.job import CapJob, BaseJobAdvert

from .browser import ManpowerBrowser


__all__ = ['ManpowerModule']


class ManpowerModule(Module, CapJob):
    NAME = 'manpower'
    DESCRIPTION = u'manpower website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    LICENSE = 'AGPLv3+'
    VERSION = '1.5'

    BROWSER = ManpowerBrowser

    type_contract_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '': u'All',
        'cdi-interimaire/c11': u'Autre',
        'formation-en-alternance/c4': u'Alternance',
        'interim/c1': u'CDD',
        'cdd/c2': u'CDI',
        'cdi/c3': u'Mission en intérim',
    }.items())])

    activityDomain_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '': u'All',
        'accueil-secretariat/s69': u'Accueil - Secrétariat',
        'achats-commerce-distribution/s66': u'Achats - Commerce - Distribution',
        'agro-alimentaire/s65': u'Agro-Alimentaire',
        'automobile/s2': u'Automobile',
        'banque-assurances-immobilier/s3': u'Banque - Assurances - Immobilier',
        'bijoux-horlogerie-lunetterie/s61': u'Bijoux - Horlogerie - Lunetterie',
        'bureau-d-etudes-methodes-qualite/s4': u'Bureau d\études- Méthodes - Qualité',
        'chimie-pharmacie-cosmetologie/s6': u'Chimie - Pharmacie - Cosmétologie',
        'communication/s73': u'Communication',
        'comptabilite-finance/s62': u'Comptabilité - Finance',
        'construction-travaux-publics/s9': u'Construction - Travaux publics',
        'electricite-electronique/s67': u'Electricité - Electronique',
        'environnement-developpement-durable/s80': u'Environnement - Développement Durable',
        'hotellerie-restauration-tourisme/s24': u'Hôtellerie- Restauration - Tourisme',
        'it-commercial-conseil-amoa/s75': u'IT - Commercial - Conseil - AMOA',
        'it-etude-et-developpement/s14': u'IT - Etude et Développement',
        'it-exploitation-systeme-sgbd/s76': u'IT - Exploitation - Système - SGBD',
        'it-reseau-telecom/s77': u'IT - Réseau - Telecom',
        'it-support-maintenance-help-desk/s78': u'IT - Support - Maintenance - Help Desk',
        'imprimerie/s12': u'Imprimerie',
        'industrie-aeronautique/s79': u'Industrie aéronautique',
        'logistique/s70': u'Logistique',
        'maintenance-entretien/s53': u'Maintenance - Entretien',
        'multimedia/s74': u'Multimédia',
        'metallurgie-fonderie/s49': u'Métallurgie- Fonderie',
        'naval/s47': u'Naval',
        'nucleaire-autres-energies/s54': u'Nucléaire - Autres Énergies',
        'papier-carton/s20': u'Papier - Carton',
        'plasturgie/s22': u'Plasturgie',
        'production-graphique/s72': u'Production Graphique',
        'production-industrielle-mecanique/s16': u'Production industrielle - Mécanique',
        'ressources-humaines-juridique/s63': u'Ressources humaines - Juridique',
        'sante/s25': u'Santé',
        'spectacle/s71': u'Spectacle',
        'surveillance-securite/s68': u'Surveillance - Sécurité',
        'textile-couture-cuir/s26': u'Textile - Couture - Cuir',
        'transport/s64': u'Transport',
        'transport-aerien/s52': u'Transport aérien',
        'teleservices-marketing-vente/s21': u'Téléservices - Marketing - Vente',
        'verre-porcelaine/s48': u'Verre - Porcelaine',
        'vin-agriculture-paysagisme/s60': u'Vin - Agriculture - Paysagisme',
    }.items())])

    places_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '': u'All',
        'alsace/r01': u'Alsace',
        'alsace/bas-rhin/r01d67': u'Bas-Rhin',
        'alsace/haut-rhin/r01d68': u'Haut-Rhin',
        'aquitaine/r02': u'Aquitaine',
        'aquitaine/dordogne/r02d24': u'Dordogne',
        'aquitaine/gironde/r02d33': u'Gironde',
        'aquitaine/landes/r02d40': u'Landes',
        'aquitaine/lot-et-garonne/r02d47': u'Lot-et-Garonne',
        'aquitaine/pyrenees-atlantiques/r02d64': u'Pyrénées-Atlantiques',
        'auvergne/r03': u'Auvergne',
        'auvergne/allier/r03d3': u'Allier',
        'auvergne/cantal/r03d15': u'Cantal',
        'auvergne/haute-loire/r03d43': u'Haute-Loire',
        'auvergne/puy-de-dome/r03d63': u'Puy-de-Dôme',
        'basse-normandie/r04': u'Basse-Normandie',
        'basse-normandie/calvados/r04d14': u'Calvados',
        'basse-normandie/manche/r04d50': u'Manche',
        'basse-normandie/orne/r04d61': u'Orne',
        'bourgogne/r05': u'Bourgogne',
        'bourgogne/cote-d-or/r05d21': u'Côte-d\'Or',
        'bourgogne/nievre/r05d58': u'Nièvre',
        'bourgogne/saone-et-loire/r05d71': u'Saône-et-Loire',
        'bourgogne/yonne/r05d89': u'Yonne',
        'bretagne/r06': u'Bretagne',
        'bretagne/cotes-d-armor/r06d22': u'Côtes-d\'Armor',
        'bretagne/finistere/r06d29': u'Finistère',
        'bretagne/ille-et-vilaine/r06d35': u'Ille-et-Vilaine',
        'bretagne/morbihan/r06d56': u'Morbihan',
        'centre/r07': u'Centre',
        'centre/cher/r07d18': u'Cher',
        'centre/eure-et-loir/r07d28': u'Eure-et-Loir',
        'centre/indre/r07d36': u'Indre',
        'centre/indre-et-loire/r07d37': u'Indre-et-Loire',
        'centre/loir-et-cher/r07d41': u'Loir-et-Cher',
        'centre/loiret/r07d45': u'Loiret',
        'champagne-ardennes/r08': u'Champagne-Ardennes',
        'champagne-ardennes/ardennes/r08d8': u'Ardennes',
        'champagne-ardennes/aube/r08d10': u'Aube',
        'champagne-ardennes/haute-marne/r08d52': u'Haute-Marne',
        'champagne-ardennes/marne/r08d51': u'Marne',
        'dom-tom/r23': u'Dom Tom',
        'dom-tom/nouvelle-caledonie/r23d98': u'Nouvelle Calédonie',
        'franche-comte/r10': u'Franche-Comté',
        'franche-comte/doubs/r10d25': u'Doubs',
        'franche-comte/haute-saone/r10d70': u'Haute-Saône',
        'franche-comte/jura/r10d39': u'Jura',
        'franche-comte/territoire-de-belfort/r10d90': u'Territoire de Belfort',
        'haute-normandie/r11': u'Haute-Normandie',
        'haute-normandie/eure/r11d27': u'Eure',
        'haute-normandie/seine-maritime/r11d76': u'Seine-Maritime',
        'ile-de-france/r12': u'Île-de-France',
        'ile-de-france/essonne/r12d91': u'Essonne',
        'ile-de-france/hauts-de-seine/r12d92': u'Hauts-de-Seine',
        'ile-de-france/paris/r12d75': u'Paris',
        'ile-de-france/seine-st-denis/r12d93': u'Seine-St-Denis',
        'ile-de-france/seine-et-marne/r12d77': u'Seine-et-Marne',
        'ile-de-france/val-d-oise/r12d95': u'Val-d\'Oise',
        'ile-de-france/val-de-marne/r12d94': u'Val-de-Marne',
        'ile-de-france/yvelines/r12d78': u'Yvelines',
        'languedoc-roussillon/r13': u'Languedoc-Roussillon',
        'languedoc-roussillon/aude/r13d11': u'Aude',
        'languedoc-roussillon/gard/r13d30': u'Gard',
        'languedoc-roussillon/herault/r13d34': u'Hérault',
        'languedoc-roussillon/lozere/r13d48': u'Lozère',
        'languedoc-roussillon/pyrenees-orientales/r13d66': u'Pyrénées-Orientales',
        'limousin/r14': u'Limousin',
        'limousin/correze/r14d19': u'Corrèze',
        'limousin/creuse/r14d23': u'Creuse',
        'limousin/haute-vienne/r14d87': u'Haute-Vienne',
        'lorraine/r15': u'Lorraine',
        'lorraine/meurthe-et-moselle/r15d54': u'Meurthe-et-Moselle',
        'lorraine/meuse/r15d55': u'Meuse',
        'lorraine/moselle/r15d57': u'Moselle',
        'lorraine/vosges/r15d88': u'Vosges',
        'midi-pyrenees/r16': u'Midi-Pyrénées',
        'midi-pyrenees/ariege/r16d9': u'Ariège',
        'midi-pyrenees/aveyron/r16d12': u'Aveyron',
        'midi-pyrenees/gers/r16d32': u'Gers',
        'midi-pyrenees/haute-garonne/r16d31': u'Haute-Garonne',
        'midi-pyrenees/hautes-pyrenees/r16d65': u'Hautes-Pyrénées',
        'midi-pyrenees/lot/r16d46': u'Lot',
        'midi-pyrenees/tarn/r16d81': u'Tarn',
        'midi-pyrenees/tarn-et-garonne/r16d82': u'Tarn-et-Garonne',
        'nord-pas-de-calais/r17': u'Nord-Pas-de-Calais',
        'nord-pas-de-calais/nord/r17d59': u'Nord',
        'nord-pas-de-calais/pas-de-calais/r17d62': u'Pas-de-Calais',
        'pays-de-la-loire/r19': u'Pays de la Loire',
        'pays-de-la-loire/loire-atlantique/r19d44': u'Loire-Atlantique',
        'pays-de-la-loire/maine-et-loire/r19d49': u'Maine-et-Loire',
        'pays-de-la-loire/mayenne/r19d53': u'Mayenne',
        'pays-de-la-loire/sarthe/r19d72': u'Sarthe',
        'pays-de-la-loire/vendee/r19d85': u'Vendée',
        'picardie/r20': u'Picardie',
        'picardie/aisne/r20d2': u'Aisne',
        'picardie/oise/r20d60': u'Oise',
        'picardie/somme/r20d80': u'Somme',
        'poitou-charentes/r21': u'Poitou-Charentes',
        'poitou-charentes/charente/r21d16': u'Charente',
        'poitou-charentes/charente-maritime/r21d17': u'Charente-Maritime',
        'poitou-charentes/deux-sevres/r21d79': u'Deux-Sèvres',
        'poitou-charentes/vienne/r21d86': u'Vienne',
        'provence-alpes-cote-d-azur/r18': u'Provence-Alpes-Côte d\'Azur',
        'provence-alpes-cote-d-azur/alpes-maritimes/r18d6': u'Alpes-Maritimes',
        'provence-alpes-cote-d-azur/alpes-de-haute-provence/r18d4': u'Alpes-de-Haute-Provence',
        'provence-alpes-cote-d-azur/bouches-du-rhone/r18d13': u'Bouches-du-Rhône',
        'provence-alpes-cote-d-azur/hautes-alpes/r18d5': u'Hautes-Alpes',
        'provence-alpes-cote-d-azur/var/r18d83': u'Var',
        'provence-alpes-cote-d-azur/vaucluse/r18d84': u'Vaucluse',
        'rhone-alpes/r22': u'Rhône-Alpes',
        'rhone-alpes/ain/r22d1': u'Ain',
        'rhone-alpes/ardeche/r22d7': u'Ardèche',
        'rhone-alpes/drome/r22d26': u'Drôme',
        'rhone-alpes/haute-savoie/r22d74': u'Haute-Savoie',
        'rhone-alpes/isere/r22d38': u'Isère',
        'rhone-alpes/loire/r22d42': u'Loire',
        'rhone-alpes/rhone/r22d69': u'Rhône',
        'rhone-alpes/savoie/r22d73': u'Savoie',
    }.items())])

    CONFIG = BackendConfig(Value('job', label='Job name', masked=False, default=''),
                           Value('place', label=u'County', choices=places_choices, default=''),
                           Value('contract', labe=u'Contract type', choices=type_contract_choices, default=''),
                           Value('activity_domain', label=u'Activity Domain', choices=activityDomain_choices,
                                 default=''),
                           )

    def advanced_search_job(self):
        for advert in self.browser.advanced_search_job(job=self.config['job'].get(),
                                                       place=self.config['place'].get(),
                                                       contract=self.config['contract'].get(),
                                                       activity_domain=self.config['activity_domain'].get()):
            yield advert

    def get_job_advert(self, _id, advert=None):
        return self.browser.get_job_advert(_id, advert)

    def search_job(self, pattern=None):
        for advert in self.browser.search_job(pattern):
            yield advert

    def fill_obj(self, advert, fields):
        return self.get_job_advert(advert.id, advert)

    OBJECTS = {BaseJobAdvert: fill_obj}
