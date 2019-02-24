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


from weboob.browser import PagesBrowser, URL

from .pages import SearchPage, AdvertPage


class ManpowerBrowser(PagesBrowser):
    BASEURL = 'https://www.manpower.fr'

    search_page = URL('/offre-emploi',
                      '/offre-emploi/(?P<query>.*)', SearchPage)
    advert_page = URL('/candidats/detail-offre-d-emploi/(?P<_id>.*).html', AdvertPage)
    error_page = URL('/offre-emploi/offre-non-trouvee')

    def search_job(self, pattern=None):
        return self.call_search(query=pattern)

    def call_search(self, query=''):
        if not query:
            return self.search_page.go().iter_job_adverts()
        return self.search_page.go(query=query).iter_job_adverts()

    def advanced_search_job(self, job='', place='', contract='', activity_domain=''):
        query1 = []
        query2 = []

        if job != '':
            query1.append(job)

        if place != '':
            _query = place.rsplit('/', 1)
            if len(_query) >= 2:
                query2.append(_query[-1])
                query1.append(_query[0])

        if contract != '':
            _query = contract.rsplit('/', 1)
            if len(_query) >= 2:
                query2.append(_query[-1])
                query1.append(_query[0])

        if activity_domain != '':
            _query = activity_domain.rsplit('/', 1)
            if len(_query) >= 2:
                query2.append(_query[-1])
                query1.append(_query[0])

        squery1 = '/'.join(query1)
        squery2 = ''.join(query2)

        if squery2 != '':
            query = '%s/%s.html' % (squery1, squery2)
        else:
            query = squery1

        return self.call_search(query=query)

    def get_job_advert(self, _id, advert):
        self.advert_page.go(_id=_id)
        if self.advert_page.is_here():
            return self.page.get_job_advert(obj=advert)
        return advert
