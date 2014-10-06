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

from weboob.deprecated.browser.decorators import id2url
from weboob.deprecated.browser import Browser
from .job import LolixJobAdvert
from .pages import SearchPage, AdvertPage
import urllib

__all__ = ['LolixBrowser']


class LolixBrowser(Browser):
    PROTOCOL = 'http'
    DOMAIN = 'fr.lolix.org/search/offre'
    ENCODING = 'iso-8859-1'

    PAGES = {
        '%s://%s/search.php' % (PROTOCOL, DOMAIN): SearchPage,
        '%s://%s/offre.php\?id=(?P<id>.+)' % (PROTOCOL, DOMAIN): AdvertPage,
    }

    def advanced_search_job(self, region=0, poste=0, contrat=0, limit_date=0, pattern=None):
        data = {
            'mode': 'find',
            'page': '0',
            'posteid': poste,
            'contratid': contrat,
            'regionid': region,
            'limitjour': limit_date
        }

        self.location('%s://%s/search.php' % (self.PROTOCOL, self.DOMAIN), urllib.urlencode(data))
        assert self.is_on_page(SearchPage)
        return self.page.iter_job_adverts(pattern)

    @id2url(LolixJobAdvert.id2url)
    def get_job_advert(self, url, advert):
        self.location(url)
        assert self.is_on_page(AdvertPage)
        return self.page.get_job_advert(url, advert)
