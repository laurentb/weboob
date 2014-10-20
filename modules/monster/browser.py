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
import urllib

from weboob.browser import PagesBrowser, URL

from .pages import SearchPage, AdvertPage

__all__ = ['MonsterBrowser']


class MonsterBrowser(PagesBrowser):

    BASEURL = 'http://offres.monster.fr'
    advert = URL('http://offre-emploi.monster.fr/(?P<_id>.*).aspx', AdvertPage)
    search = URL('rechercher\?q=(?P<pattern>.*)',
                 'PowerSearch.aspx\?q=(?P<job_name>.*)&where=(?P<place>.*)&jt=(?P<contract>.*)&occ=(?P<job_category>.*)&tm=(?P<limit_date>.*)&indid=(?P<activity_domain>)',
                 'rechercher/.*',
                 SearchPage)

    def search_job(self, pattern=None):
        return self.search.go(pattern=urllib.quote_plus(pattern)).iter_job_adverts()

    def advanced_search_job(self, job_name, place, contract, job_category, activity_domain, limit_date):
        return self.search.go(job_name=job_name, place=place, contract=contract, job_category=job_category,
                              limit_date=limit_date, activity_domain=activity_domain).iter_job_adverts()

    def get_job_advert(self, _id, advert):
        return self.advert.go(_id=_id).get_job_advert(obj=advert)
