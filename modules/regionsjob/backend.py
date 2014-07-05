# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
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
from weboob.capabilities.job import CapJob, BaseJobAdvert
from .browser import RegionsjobBrowser
from weboob.tools.ordereddict import OrderedDict
from weboob.tools.value import Value


__all__ = ['RegionsjobBackend']


class RegionsjobBackend(BaseBackend, CapJob):
    NAME = 'regionsjob'
    DESCRIPTION = u'regionsjob website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    LICENSE = 'AGPLv3+'
    VERSION = '0.j'

    BROWSER = RegionsjobBrowser

    website_choices = OrderedDict([(k, u'%s (%s)' % (v, k)) for k, v in sorted({
        'www.centrejob.com': u'CentreJob',
        'www.estjob.com': u'EstJob',
        'www.nordjob.com': u'NordJob',
        'www.ouestjob.com': u'OuestJob',
        'www.pacajob.com': u'PacaJob',
        'www.parisjob.com': u'ParisJob',
        'www.rhonealpesjob.com': u'RhoneAlpesJob',
        'www.sudouestjob.com': u'SudOuestJob',
        'www.jobtrotter.com': u'JobTrotter',
    }.iteritems())])

    fonction_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '000000': u'indifferent',
        '4': u'Achat',
        '20': u'Assistanat/Adm.ventes/Accueil',
        '1': u'BTP - Gros Oeuvre/Second Oeuvre',
        '37': u'Bureau d\'Etudes/R&amp;D/BTP archi/conception',
        '39': u'Commercial - Technico-Commercial',
        '31': u'Commercial auprès des particuliers',
        '30': u'Commercial auprès des professionnels',
        '5': u'Commercial-Vendeur en magasin',
        '6': u'Compta/Gestion/Finance/Audit',
        '34': u'Direction/Resp. Co. et Centre de Profit',
        '21': u'Import/Export/International',
        '22': u'Informatique - Dével. Hardware',
        '7': u'Informatique - Développement',
        '9': u'Informatique - Systèmes d\'Information',
        '10': u'Informatique - Systèmes/Réseaux',
        '11': u'Ingénierie - Agro/Agri',
        '12': u'Ingénierie - Chimie/Pharmacie/Bio.',
        '13': u'Ingénierie - Electro-tech./Automat.',
        '14': u'Ingénierie - Mécanique/Aéron.',
        '15': u'Ingénierie-Telecoms/Electronique',
        '44': u'Juridique/Droit',
        '36': u'Logistique/Métiers du Transport  ',
        '16': u'Marketing/Communication/Graphisme',
        '45': u'Métiers de la distribution - Management/Resp.',
        '40': u'Métiers de la Fonction Publique ',
        '43': u'Négociation/Gestion immobilière',
        '17': u'Production - Gestion/Maintenance',
        '41': u'Production - Opérateur/Manoeuvre',
        '18': u'Qualité/Hygiène/Sécurité/Environnement',
        '26': u'Restauration/Tourisme/Hôtellerie/Loisirs',
        '19': u'RH/Personnel/Formation',
        '25': u'Santé/Social',
        '35': u'SAV/Hotline/Téléconseiller',
        '42': u'Services à la personne/aux entreprises',
    }.iteritems())])

    secteur_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '000000': u'indifferent',
        '14': u'Agriculture/Pêche',
        '9': u'Banque/Assurance/Finance',
        '3': u'BTP',
        '4': u'Distribution/Commerce de gros',
        '17': u'Enseignement/Formation',
        '15': u'Immobilier',
        '18': u'Industrie Aéronautique/Aérospatial',
        '2': u'Industrie Agro-alimentaire',
        '5': u'Industrie Auto/Meca/Navale',
        '6': u'Industrie high-tech/Telecom',
        '19': u'Industrie Manufacturière',
        '20': u'Industrie Pétrolière/Pétrochimie',
        '21': u'Industrie Pharmaceutique/Biotechn./Chimie',
        '7': u'Média/Internet/Communication',
        '10': u'Restauration',
        '8': u'Santé/Social/Association',
        '22': u'Secteur Energie/Environnement',
        '11': u'Secteur informatique/SSII',
        '27': u'Service public autres',
        '1': u'Service public d''etat',
        '25': u'Service public des collectivités territoriales',
        '26': u'Service public hospitalier',
        '13': u'Services aux Entreprises',
        '23': u'Services aux Personnes/Particuliers',
        '24': u'Tourisme/Hôtellerie/Loisirs',
        '16': u'Transport/Logistique',
    }.iteritems())])

    experience_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '000000': u'Indifférent',
        '7': u'BEP/CAP',
        '4': u'Employé/Opérateur/Ouvrier Spe/Bac',
        '3': u'Technicien/Employé Bac +2',
        '6': u'Agent de maîtrise/Bac +3/4',
        '2': u'Ingénieur/Cadre/Bac +5',
        '1': u'Cadre dirigeant',
    }.iteritems())])

    contract_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '000000': u'Indifférent',
        '6': u'Alternance',
        '1': u'CDD',
        '2': u'CDI',
        '8': u'Franchise',
        '7': u'Indépendant',
        '3': u'Stage',
        '4': u'Travail temporaire',
    }.iteritems())])

    CONFIG = BackendConfig(Value('website', label=u'Region', choices=website_choices),
                           Value('metier', label='Job name', masked=False, default=''),
                           Value('fonction', label=u'Fonction', choices=fonction_choices, default='000000'),
                           Value('secteur', label=u'Secteur', choices=secteur_choices, default='000000'),
                           Value('contract', label=u'Contract', choices=contract_choices, default='000000'),
                           Value('experience', label=u'Experience', choices=experience_choices, default='000000'),
                           )

    def create_default_browser(self):
        return self.create_browser(self.config['website'].get())

    def search_job(self, pattern=''):
        return self.browser.search_job(pattern=pattern)

    def advanced_search_job(self):
        return self.browser.search_job(pattern=self.config['metier'].get(),
                                       fonction=int(self.config['fonction'].get()),
                                       secteur=int(self.config['secteur'].get()),
                                       contract=int(self.config['contract'].get()),
                                       experience=int(self.config['experience'].get()))

    def get_job_advert(self, _id, advert=None):
        return self.browser.get_job_advert(_id, advert)

    def fill_obj(self, advert, fields):
        return self.get_job_advert(advert.id, advert)

    OBJECTS = {BaseJobAdvert: fill_obj}
