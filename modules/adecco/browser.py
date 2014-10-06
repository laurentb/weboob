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
from .job import AdeccoJobAdvert
from .pages import SearchPage, AdvertPage
import urllib

__all__ = ['AdeccoBrowser']


class AdeccoBrowser(Browser):
    PROTOCOL = 'http'
    DOMAIN = 'www.adecco.fr'
    ENCODING = None

    PAGES = {
        '%s://%s/trouver-un-emploi/Pages/Offres-d-emploi.aspx?(.*)$' % (PROTOCOL, DOMAIN): SearchPage,
        '%s://%s/trouver-un-emploi/Pages/Details-de-l-Offre/(.*?)/(.*?).aspx\?IOF=(.*?)$' % (PROTOCOL, DOMAIN): AdvertPage,
    }

    def search_job(self, pattern=None):
        self.location('%s://%s/trouver-un-emploi/Pages/Offres-d-emploi.aspx?keywords=%s'
                      % (self.PROTOCOL, self.DOMAIN, pattern.replace(' ', '+')))
        assert self.is_on_page(SearchPage)
        return self.page.iter_job_adverts()

    def advanced_search_job(self, publication_date=None, contract_type=None, conty=None, region=None, job_category=None, activity_domain=None):
        data = {
            'publicationDate': publication_date,
            'department': conty,
            'region': region,
            'jobCategory': job_category,
            'activityDomain': activity_domain,
            'contractTypes': contract_type,
        }
        self.location('%s://%s/trouver-un-emploi/Pages/Offres-d-emploi.aspx?%s'
                      % (self.PROTOCOL, self.DOMAIN, urllib.urlencode(data)))
        assert self.is_on_page(SearchPage)
        return self.page.iter_job_adverts()

    @id2url(AdeccoJobAdvert.id2url)
    def get_job_advert(self, url, advert):
        self.location(url)
        assert self.is_on_page(AdvertPage)
        return self.page.get_job_advert(url, advert)
