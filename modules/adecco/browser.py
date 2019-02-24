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

from weboob.browser import PagesBrowser, URL
from weboob.tools.compat import quote_plus

from .pages import SearchPage, AdvertPage, AdvertsJsonPage

from datetime import date, timedelta

__all__ = ['AdeccoBrowser']


class AdeccoBrowser(PagesBrowser):
    BASEURL = 'https://www.adecco.fr'
    TIMEOUT = 30

    search_page = URL('/resultats-offres-emploi/\?k=(?P<job>.*)&l=(?P<town>.*)&display=50',
                      '/resultats-offres-emploi/(?P<q>.*)/\?display=50',
                      SearchPage)
    json_page = URL('/AdeccoGroup.Global/api/Job/AsynchronousJobSearch/', AdvertsJsonPage)
    advert_page = URL('/offres-d-emploi/\?ID=(?P<_id>.*)',
                      '/offres-d-emploi/.*',
                      AdvertPage)

    def call_json(self, params, date_min=None):
        self.session.headers.update({"Accept": "application/json, text/javascript, */*; q=0.01",
                                     "X-Requested-With": "XMLHttpRequest"})
        return self.json_page.go(data=params).iter_job_adverts(data=params, date_min=date_min)

    def search_job(self, pattern=None):
        if pattern:
            return self.advanced_search_job(job=pattern)
        return []

    def advanced_search_job(self, publication_date=0, contract_type=None, conty=None, activity_domain=None,
                            job='', town=''):

        params = self.search_page.go(job=quote_plus(job.encode('utf-8')),
                                     town=quote_plus(town.encode('utf-8'))).get_post_params()

        if contract_type:
            self.page.url += '&employmenttype=%s' % contract_type

        if conty:
            self.page.url += '&countrysubdivisionfacet=%s' % conty

        if activity_domain:
            self.page.url += '&industryfacet=%s' % activity_domain

        date_min = date.today() - timedelta(days=publication_date) if publication_date > 0 else None
        params['filterUrl'] = self.page.url
        return self.call_json(params, date_min=date_min)

    def get_job_advert(self, _id, advert):
        return self.advert_page.go(_id=_id).get_job_advert(obj=advert)
