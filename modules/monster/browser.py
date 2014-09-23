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

from weboob.tools.browser.decorators import id2url
from weboob.tools.browser import Browser

from .pages import SearchPage, AdvertPage
from .job import MonsterJobAdvert

__all__ = ['MonsterBrowser']


class MonsterBrowser(Browser):
    PROTOCOL = 'http'
    DOMAIN = 'offres.monster.fr'
    ENCODING = 'utf-8'

    PAGES = {
        '%s://%s/offres-d-emploi/\?q=(.*?)' % (PROTOCOL, DOMAIN): SearchPage,
        '%s://%s/rechercher/(.*?)' % (PROTOCOL, DOMAIN): SearchPage,
        'http://offre-emploi.monster.fr/(.*?).aspx': AdvertPage,
    }

    def search_job(self, pattern=None):
        self.location('%s://%s/offres-d-emploi/?q=%s'
                      % (self.PROTOCOL, self.DOMAIN, urllib.quote_plus(pattern.encode(self.ENCODING))))
        assert self.is_on_page(SearchPage)
        return self.page.iter_job_adverts()

    def advanced_search_job(self, job_name, place, contract, job_category, activity_domain, limit_date):
        self.location(
            '%s://%s/PowerSearch.aspx?q=%s&where=%s&jt=%s&occ=%s&tm=%s&indid=%s' % (self.PROTOCOL,
                                                                                    self.DOMAIN,
                                                                                    urllib.quote(
                                                                                        job_name.encode(self.ENCODING)),
                                                                                    place,
                                                                                    contract,
                                                                                    job_category,
                                                                                    limit_date,
                                                                                    activity_domain))
        assert self.is_on_page(SearchPage)
        return self.page.iter_job_adverts()

    @id2url(MonsterJobAdvert.id2url)
    def get_job_advert(self, url, advert):
        self.location(url)
        assert self.is_on_page(AdvertPage)
        return self.page.get_job_advert(url, advert)
