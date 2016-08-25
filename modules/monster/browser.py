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

from .pages import AdvertPage, AdvSearchPage, ExpiredAdvert

__all__ = ['MonsterBrowser']


class MonsterBrowser(PagesBrowser):
    BASEURL = 'http://www.monster.fr'

    advert = URL('http://offre-emploi.monster.fr/v2/job/View\?JobID=(?P<_id>.*)', AdvertPage)
    expired_advert = URL('http://offre-emploi.monster.fr/v2/job/Expired\?JobId=(?P<_id>.*)', ExpiredAdvert)
    adv_search = URL('/emploi/recherche/(?P<search>.*)&page=(?P<page>\d*)',
                     AdvSearchPage)

    def search_job(self, pattern=None):
        return self.adv_search.go(search='?q=%s' % urllib.quote_plus(pattern), page=1).iter_job_adverts()

    def advanced_search_job(self, job_name, place, contract, limit_date):
        search = '' if not contract else contract
        query = {'q': urllib.quote_plus(job_name),
                 'where': place,
                 'tm': limit_date}
        return self.adv_search.go(search='%s?%s' % (search, urllib.urlencode(query)), page=1).iter_job_adverts()

    def get_job_advert(self, _id, advert):
        return self.advert.go(_id=_id).get_job_advert(obj=advert)
