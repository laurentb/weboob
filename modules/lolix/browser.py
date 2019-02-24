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
from .pages import SearchPage, AdvertPage

__all__ = ['LolixBrowser']


class LolixBrowser(PagesBrowser):
    BASEURL = 'http://fr.lolix.org'
    ENCODING = 'iso-8859-1'

    search_page = URL('/search/offre/search.php', SearchPage)
    advert_page = URL('/search/offre/offre.php\?id=(?P<id>.+)', AdvertPage)

    def advanced_search_job(self, region=0, poste=0, contrat=0, limit_date=0, pattern=None):
        data = {
            'mode': 'find',
            'page': '0',
            'posteid': poste,
            'contratid': contrat,
            'regionid': region,
            'limitjour': limit_date
        }

        return self.search_page.go(data=data).iter_job_adverts(pattern=pattern)

    def get_job_advert(self, id, advert):
        return self.advert_page.go(id=id).get_job_advert(obj=advert)
