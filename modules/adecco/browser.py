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

from weboob.browser import PagesBrowser, URL

from .pages import SearchPage, AdvertPage

import urllib

__all__ = ['AdeccoBrowser']


class AdeccoBrowser(PagesBrowser):

    BASEURL = 'http://www.adecco.fr/'

    search_page = URL('trouver-un-emploi/Pages/Offres-d-emploi.aspx\?(?P<query>.*)', SearchPage)
    advert_page = URL('trouver-un-emploi/Pages/Details-de-l-Offre/(?P<part1>.*)/(?P<part2>.*).aspx\?IOF=(?P<part3>.*)',
                      AdvertPage)

    def search_job(self, pattern=None):
        query = {'keywords': urllib.quote_plus(pattern)}
        return self.search_page.go(query=urllib.urlencode(query)).iter_job_adverts()

    def advanced_search_job(self, publication_date=None, contract_type=None, conty=None, region=None, job_category=None,
                            activity_domain=None):
        data = {
            'publicationDate': publication_date,
            'department': conty,
            'region': region,
            'jobCategory': job_category,
            'activityDomain': activity_domain,
            'contractTypes': contract_type,
        }
        return self.search_page.go(query=urllib.urlencode(data)).iter_job_adverts()

    def get_job_advert(self, _id, advert):
        splitted_id = _id.split('/')
        return self.advert_page.go(part1=splitted_id[0],
                                   part2=splitted_id[1],
                                   part3=splitted_id[2]).get_job_advert(obj=advert)
