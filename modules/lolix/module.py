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

from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value
from weboob.capabilities.job import CapJob, BaseJobAdvert

from .browser import LolixBrowser

__all__ = ['LolixModule']


class LolixModule(Module, CapJob):
    NAME = 'lolix'
    DESCRIPTION = u'Lolix French free software employment website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    VERSION = '1.5'
    LICENSE = 'AGPLv3+'

    BROWSER = LolixBrowser

    region_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '0': u'-- Indifférent --',
        '100000000': u'-- France entière',
        '100100000': u'-- France métropolitaine',
        '100100001': u'-- Alsace',
        '100100002': u'-- Auvergne',
        '100100003': u'-- Aquitaine',
        '100100004': u'-- Bourgogne',
        '100100005': u'-- Bretagne',
        '100100025': u'-- Centre',
        '100100027': u'-- Champagne-Ardenne',
        '100100030': u'-- Corse',
        '100100037': u'-- Franche-Comté',
        '100100040': u'-- Ile de France',
        '100100044': u'-- Languedoc-Roussillon',
        '100100048': u'-- Limousin',
        '100100051': u'-- Lorraine',
        '100100055': u'-- Midi-Pyrénées',
        '100100060': u'-- Nord-Pas-de-Calais',
        '100100073': u'-- Normandie',
        '100100076': u'-- Pays-de-Loire',
        '100100079': u'-- Picardie',
        '100100082': u'-- Poitou-Charentes',
        '100100085': u'-- Provence Alpes Cote d\'azur',
        '100100090': u'-- Rhône Alpes',
        '100200000': u'-- DOM et TOM',
        '100200001': u'-- Guadeloupe',
        '100200002': u'-- Guyane',
        '100200003': u'-- Martinique',
        '100200004': u'-- Réunion',
        '100200005': u'-- Saint-Pierre et Miquelon',
        '200000000': u'-- Etranger',
    }.items())])

    poste_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '0': u'-- Indifférent --',
        '100000000': u'-- Service Technique',
        '100005000': u'-- Administrateur base de données',
        '100004000': u'-- Admin. Système/Réseaux',
        '100004004': u'-- Administrateur système',
        '100004002': u'-- Administrateur réseaux',
        '100007000': u'-- Analyste',
        '100002000': u'-- Chef de projet',
        '100002001': u'-- Chef de projet junior',
        '100002002': u'-- Chef de projet senior',
        '100021000': u'-- Consultant',
        '100003000': u'-- Développeur',
        '100003001': u'-- Développeur junior',
        '100003002': u'-- Développeur senior',
        '100009000': u'-- Directeur technique',
        '100006000': u'-- Ingénieur d\'étude',
        '100011000': u'-- Ingénieur support',
        '100012000': u'-- Responsable R & D',
        '100010000': u'-- Technicien',
        '100010002': u'-- Technicien hotline',
        '100010003': u'-- Technicien maintenance',
        '100020000': u'-- Webmaster',
        '200000000': u'-- Service Commercial',
        '200300000': u'-- Commercial',
        '200200000': u'-- Directeur commercial',
        '200100000': u'-- Technico commercial',
        '400000000': u'-- Service Marketing',
        '400100000': u'-- Responsable Marketing',
        '300000000': u'-- Service qualité',
        '300100000': u'-- Assistant qualité',
        '300200000': u'-- Responsable qualité',
        '2000000': u'-- Fondateur',
        '7000000': u'-- Formateur',
        '6000000': u'-- Journaliste',
        '500100000': u'-- Assistant(e) de direction',
        '4000000': u'-- Stagiaire',
        '5000000': u'-- Traducteur',
    }.items())])

    '''
        '000000' in order to display description in console question
        the rule is  : len(key) > 5 or ' ' in key:
    '''
    contrat_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '000000': u'-- Indifférent --',
        '6': u'Alternance',
        '5': u'Apprentissage',
        '2': u'CDD',
        '1': u'CDI',
        '4': u'Freelance',
        '3': u'Stage',
    }.items())])

    limit_date_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '2592000': u'30 jours',
        '5184000': u'60 jours',
        '7776000': u'90 jours',
        '0': u'Illimitée',
    }.items())])

    CONFIG = BackendConfig(Value('region', label=u'Région', choices=region_choices),
                           Value('poste', label=u'Poste', choices=poste_choices),
                           Value('contrat', label=u'Contrat', choices=contrat_choices),
                           Value('limit_date', label=u'Date limite', choices=limit_date_choices))

    def search_job(self, pattern=None):
        return self.browser.advanced_search_job(pattern=pattern)

    def advanced_search_job(self):
        for advert in self.browser.advanced_search_job(region=self.config['region'].get(),
                                                       poste=self.config['poste'].get(),
                                                       contrat=int(self.config['contrat'].get()),
                                                       limit_date=self.config['limit_date'].get()):
            yield advert

    def get_job_advert(self, _id, advert=None):
        return self.browser.get_job_advert(_id, advert)

    def fill_obj(self, advert, fields):
        self.get_job_advert(advert.id, advert)

    OBJECTS = {BaseJobAdvert: fill_obj}
