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
from weboob.capabilities.job import CapJob, BaseJobAdvert
from weboob.tools.value import Value

from .browser import MonsterBrowser

__all__ = ['MonsterModule']


class MonsterModule(Module, CapJob):
    NAME = 'monster'
    DESCRIPTION = u'monster website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    LICENSE = 'AGPLv3+'
    VERSION = '2.0'

    BROWSER = MonsterBrowser

    type_contrat_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        'Interim-ou-CDD-ou-mission_8': u'Interim ou CDD ou mission',
        'CDI_8': u'CDI',
        'Stage-Apprentissage-Alternance_8': u'Stage/Apprentissage/Alternance',
        ' ': u'Autres',
        'Indépendant-Freelance-Saisonnier-Franchise_8': u'Indépendant/Freelance/Saisonnier/Franchise',
        'Journalier_8': u'Journalier',
        'Temps-Partiel_8': u'Temps Partiel',
        'Temps-Plein_8': u'Temps Plein',
    }.items())])

    date_choices = OrderedDict([(k, u'%s' % (v)) for k, v in sorted({
        '-1': u'N importe quelle date',
        '000000': u'Aujourd hui',
        '1': u'2 derniers jours',
        '3': u'3 derniers jours',
        '7': u'Les 7 derniers jours',
        '14': u'Les 14 derniers jours',
        '30': u'30 derniers jours',
    }.items())])

    CONFIG = BackendConfig(
        Value('job_name', label='Job name', masked=False, default=''),
        Value('place', label='Place', masked=False, default=''),
        Value('contract', label=u'Contract', choices=type_contrat_choices, default=''),
        Value('limit_date', label=u'Date', choices=date_choices, default='-1'),
    )

    def search_job(self, pattern=None):
        return self.browser.search_job(pattern)

    def advanced_search_job(self):
        return self.browser.advanced_search_job(job_name=self.config['job_name'].get(),
                                                place=self.config['place'].get(),
                                                contract=self.config['contract'].get(),
                                                limit_date=self.config['limit_date'].get())

    def get_job_advert(self, _id, advert=None):
        return self.browser.get_job_advert(_id, advert)

    def fill_obj(self, advert, fields):
        return self.get_job_advert(advert.id, advert)

    OBJECTS = {BaseJobAdvert: fill_obj}
