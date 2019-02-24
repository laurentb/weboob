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
import requests

from .job import APEC_CONTRATS, APEC_EXPERIENCE

from weboob.browser.elements import ItemElement, method, DictElement
from weboob.browser.pages import JsonPage, pagination
from weboob.browser.filters.standard import DateTime, Format, Regexp
from weboob.browser.filters.json import Dict
from weboob.browser.filters.html import CleanHTML
from weboob.capabilities.job import BaseJobAdvert
from weboob.capabilities.base import NotAvailable


class IdsPage(JsonPage):

    def get_adverts_number(self):
        return self.doc['totalCount']

    @pagination
    @method
    class iter_job_adverts(DictElement):
        item_xpath = 'resultats'

        def next_page(self):
            self.page.browser.start += self.env['range']
            if self.page.browser.start <= self.env['count']:
                data = self.page.browser.create_parameters(pattern=self.env['pattern'],
                                                           fonctions=self.env['fonctions'],
                                                           lieux=self.env['lieux'],
                                                           secteursActivite=self.env['secteursActivite'],
                                                           typesContrat=self.env['typesContrat'],
                                                           typesConvention=self.env['typesConvention'],
                                                           niveauxExperience=self.env['niveauxExperience'],
                                                           salaire_min=self.env['salaire_min'],
                                                           salaire_max=self.env['salaire_max'],
                                                           date_publication=self.env['date_publication'],
                                                           start=self.page.browser.start,
                                                           range=self.env['range'])

                return requests.Request("POST", self.page.url, data=data)

        class item(ItemElement):
            klass = BaseJobAdvert
            obj_id = Regexp(Dict('@uriOffre'), '.*=(.*)')


class OffrePage(JsonPage):
    @method
    class get_job_advert(ItemElement):
        klass = BaseJobAdvert

        obj_id = Dict('numeroOffre')
        obj_title = Dict('intitule')
        obj_description = CleanHTML(Dict('texteHtml'))
        obj_job_name = Dict('intitule')
        obj_publication_date = DateTime(Dict('datePublication'))
        obj_society_name = Dict('nomCommercialEtablissement', default=NotAvailable)

        def obj_contract_type(self):
            ctr = '%s' % Dict('idNomTypeContrat')(self)
            return APEC_CONTRATS.get(ctr) if ctr in APEC_CONTRATS else NotAvailable

        obj_place = Dict('lieux/0/libelleLieu')
        obj_pay = Dict('salaireTexte')

        def obj_experience(self):
            exp = u'%s' % Dict('idNomNiveauExperience')(self)
            return APEC_EXPERIENCE.get(exp) if exp in APEC_EXPERIENCE else NotAvailable

        obj_url = Format('https://cadres.apec.fr/home/mes-offres/recherche-des-offres-demploi/liste-des-offres-demploi/detail-de-loffre-demploi.html?numIdOffre=%s', Dict('numeroOffre'))
