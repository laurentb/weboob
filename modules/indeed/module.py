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

from collections import OrderedDict

from weboob.tools.backend import Module, BackendConfig
from weboob.capabilities.job import CapJob, BaseJobAdvert
from weboob.tools.value import Value

from .browser import IndeedBrowser

__all__ = ['IndeedModule']


class IndeedModule(Module, CapJob):
    NAME = 'indeed'
    DESCRIPTION = u'indeed website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    LICENSE = 'AGPLv3+'
    VERSION = '1.4'

    BROWSER = IndeedBrowser

    type_contrat_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        'all': u'Tous les emplois',
        'fulltime': u'Temps plein',
        'parttime': u'Temps partiel',
        'contract': u'Durée indéterminée',
        'internship': u'Stage / Apprentissage',
        'temporary': u'Durée déterminée',
    }.items())])

    limit_date_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        'any': u'à tout moment',
        '15': u'depuis 15 jours',
        '7': u'depuis 7 jours',
        '3': u'depuis 3 jours',
        '1': u'depuis hier',
        'last': u'depuis ma dernière visite',
    }.items())])

    radius_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '0': u'uniquement à cet endroit',
        '5': u'dans un rayon de 5 kilomètres',
        '10': u'dans un rayon de 10 kilomètres',
        '15': u'dans un rayon de 15 kilomètres',
        '25': u'dans un rayon de 25 kilomètres',
        '50': u'dans un rayon de 50 kilomètres',
        '100': u'dans un rayon de 100 kilomètres',
    }.items())])

    CONFIG = BackendConfig(Value('metier', label=u'Job name', masked=False, default=''),
                           Value('limit_date', label=u'Date limite', choices=limit_date_choices, default=''),
                           Value('contrat', label=u'Contract', choices=type_contrat_choices, default=''),
                           Value('place', label=u'Place', masked=False, default=''),
                           Value('radius', label=u'Radius', choices=radius_choices, default=''))

    def search_job(self, pattern=None):
        return self.browser.search_job(metier=pattern)

    def advanced_search_job(self):
        return self.browser.search_job(metier=self.config['metier'].get(),
                                       limit_date=self.config['limit_date'].get(),
                                       contrat=self.config['contrat'].get(),
                                       place=self.config['place'].get(),
                                       radius=self.config['radius'].get())

    def get_job_advert(self, _id, advert=None):
        return self.browser.get_job_advert(_id, advert)

    def fill_obj(self, advert, fields):
        return self.get_job_advert(advert.id, advert)

    OBJECTS = {BaseJobAdvert: fill_obj}
