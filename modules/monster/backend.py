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

from .browser import MonsterBrowser
from .job import MonsterJobAdvert

__all__ = ['MonsterBackend']


class MonsterBackend(BaseBackend, ICapJob):
    NAME = 'monster'
    DESCRIPTION = u'monster website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    LICENSE = 'AGPLv3+'
    VERSION = '0.j'

    BROWSER = MonsterBrowser

    type_contrat_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '97': u'Interim ou CDD ou mission',
        '98': u'CDI',
        '99': u'Stage',
        '000100': u'Autres',
        '101': u'Indépendant/Freelance/Franchise',
        '102': u'Journalier',
        '103': u'Titulaire de la fonction publique',
        '104': u'Temps Partiel',
        '105': u'Temps Plein',
    }.iteritems())])

    JobCategory_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        ' ': u'Choisir…',
        '78': u'Architecture, Création et Spectacle',
        '92': u'Autres',
        '76': u'BTP et second oeuvre',
        '95': u'Commercial / Vente',
        '72': u'Comptabilité et Finance',
        '80': u'Edition et Ecriture',
        '81': u'Formation / Education',
        '93': u'Gestion de projet / programme',
        '83': u'Hôtellerie, Restauration et Tourisme',
        '86': u'Informatique et Technologies',
        '82': u'Ingénierie',
        '85': u'Installation, Maintenance et Réparation',
        '87': u'Juridique',
        '88': u'Logistique, Approvisionnement et Transport',
        '90': u'Marketing',
        '89': u'Production et Opérations',
        '94': u'Qualité / Inspection',
        '75': u'Recherche et Analyses',
        '84': u'Ressources Humaines',
        '91': u'Santé',
        '96': u'Sécurité',
        '73': u'Services administratifs',
        '79': u'Services clientèle et aux particuliers',
        '77': u'Stratégie et Management',
    }.iteritems())])

    activityDomain_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        ' ': u'Choisir…',
        '16': u'Aéronautique / Aérospatiale (civil et militaire)',
        '17': u'Agriculture / Sylviculture / Pêche / Chasse',
        '39': u'Agroalimentaire',
        '18': u'Architecture / Design et services associés',
        '53': u'Art / Culture / Loisirs',
        '51': u'Associations / Bénévolat',
        '43': u'Assurance et Mutualité',
        '23': u'Audiovisuel / Media / Diffusion Audio et Vidéo',
        '14': u'Audit / Comptabilité / Fiscalité',
        '20': u'Automobile - Vente, Maintenance et Réparations',
        '52': u'Autres',
        '24': u'Autres Services aux entreprises',
        '21': u'Banques / Organismes financiers',
        '32': u'Biens de consommation courante / Cosmétiques',
        '31': u'BTP / Construction - bâtiments commerciaux, habitations',
        '30': u'BTP / Construction - usines, infrastructures, TP',
        '45': u'Cabinets et Services Juridiques',
        '46': u'Cabinets conseils en Management et Stratégie',
        '25': u'Chimie',
        '67': u'Commerce de gros et Import/Export',
        '55': u'Edition / Imprimerie',
        '35': u'Energie et Eau',
        '33': u'Enseignement et Formation',
        '66': u'Gestion des déchêts et Recyclage',
        '59': u'Grande Distribution et Commerce de détail',
        '42': u'Hôtellerie',
        '56': u'Immobilier',
        '47': u'Industrie / Production, autres',
        '19': u'Industrie Automobile - Constructeurs / Équipementiers',
        '34': u'Industrie électronique',
        '22': u'Industrie pharmaceutique / Biotechnologies',
        '26': u'Industrie Textile, Cuir et Confection',
        '27': u'Informatique - Hardware',
        '29': u'Informatique - Services',
        '28': u'Informatique - Software',
        '36': u'Ingénierie et services associés',
        '44': u'Internet / e-commerce',
        '57': u'Location',
        '48': u'Marine / Aéronautique',
        '15': u'Marketing / Communication / Publicité / RP',
        '50': u'Métaux et Minéraux',
        '37': u'Parcs d attraction et salles de spectacles',
        '62': u'Recrutement / Intérim et bureaux de placement',
        '58': u'Restauration',
        '41': u'Santé',
        '49': u'Santé - Equipement et appareils',
        '40': u'Secteur Public',
        '60': u'Sécurité et Surveillance',
        '54': u'Services aux particuliers',
        '38': u'Services financiers',
        '61': u'Sport - Equipements et infrastructures',
        '63': u'Télécommunication',
        '65': u'Tourisme, voyages et transport de personnes',
        '64': u'Transport de marchandises, entreprosage, stockage',
    }.iteritems())])

    date_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '-1': u'N importe quelle date',
        '000000': u'Aujourd hui',
        '1': u'2 derniers jours',
        '3': u'3 derniers jours',
        '7': u'Les 7 derniers jours',
        '14': u'Les 14 derniers jours',
        '30': u'30 derniers jours',
    }.iteritems())])

    CONFIG = BackendConfig(
        Value('job_name', label='Job name', masked=False, default=''),
        Value('place', label='Place', masked=False, default=''),
        Value('contract', label=u'Contract', choices=type_contrat_choices, default='000100'),
        Value('job_category', label=u'Job Category', choices=JobCategory_choices, default=''),
        Value('activity_domain', label=u'Activity Domain', choices=activityDomain_choices, default=''),
        Value('limit_date', label=u'Date', choices=date_choices, default='-1'),
    )

    def search_job(self, pattern=None):
        with self.browser:
            for advert in self.browser.search_job(pattern):
                yield advert

    def advanced_search_job(self):
        with self.browser:
            for advert in self.browser.advanced_search_job(job_name=self.config['job_name'].get(),
                                                           place=self.config['place'].get(),
                                                           contract=self.config['contract'].get(),
                                                           job_category=self.config['job_category'].get(),
                                                           activity_domain=self.config['activity_domain'].get(),
                                                           limit_date=self.config['limit_date'].get()):
                yield advert

    def get_job_advert(self, _id, advert=None):
        with self.browser:
            return self.browser.get_job_advert(_id, advert)

    def fill_obj(self, advert, fields):
        self.get_job_advert(advert.id, advert)

    OBJECTS = {MonsterJobAdvert: fill_obj}
