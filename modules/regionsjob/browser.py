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

from weboob.browser import PagesBrowser, URL

from .pages import SearchPage, AdvertPage

__all__ = ['RegionsjobBrowser']


class RegionsjobBrowser(PagesBrowser):

    search_page = URL('emplois/recherche.html\?.*', SearchPage)
    advert_page = URL('emplois/(?P<_id>.*)\.html', AdvertPage)

    def __init__(self, website, *args, **kwargs):
        self.BASEURL = 'http://%s/' % website
        PagesBrowser.__init__(self, *args, **kwargs)

    def search_job(self, pattern='', fonction='', secteur='', contract='',
                   experience='', qualification='', enterprise_type=''):

        params = {'k': pattern.encode('utf-8')}

        if fonction:
            params['f'] = fonction

        if qualification:
            params['q'] = qualification

        if contract:
            params['c'] = contract

        if experience:
            params['e'] = experience

        if secteur:
            params['s'] = secteur

        if enterprise_type:
            params['et'] = enterprise_type

        return self.search_page.go(params=params).iter_job_adverts(domain=self.BASEURL)

    def get_job_advert(self, _id, advert):
        splitted_id = _id.split('#')
        self.BASEURL = 'http://www.%s.com/' % splitted_id[0]
        return self.advert_page.go(_id=splitted_id[1]).get_job_advert(obj=advert)
