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


from weboob.tools.browser import BaseBrowser

from weboob.tools.browser.decorators import id2url
from .pages import SearchPage, AdvertPage
from .job import IndeedJobAdvert


__all__ = ['IndeedBrowser']


class IndeedBrowser(BaseBrowser):
    PROTOCOL = 'http'
    DOMAIN = 'www.indeed.fr'
    ENCODING = None
    PAGES = {
        '%s://%s/Emplois-(.*?)' % (PROTOCOL, DOMAIN): SearchPage,
        '%s://%s/emplois(.*?)' % (PROTOCOL, DOMAIN): SearchPage,
        '%s://%s/cmp/(.*?)' % (PROTOCOL, DOMAIN): AdvertPage,
    }

    def search_job(self, pattern=None, metier=None, place=None, contrat=None):
        self.location('http://www.indeed.fr/emplois?as_and=%s&limit=50&sort=date&st=employer&sr=directhire'
                      % pattern.replace(' ', '+'))
        assert self.is_on_page(SearchPage)
        return self.page.iter_job_adverts()

    def advanced_search_job(self, metier=None, contrat=None, limit_date=None):
        self.location('http://www.indeed.fr/emplois?as_ttl=%s&limit=50&sort=date&st=employer&sr=directhire&jt=%s&fromage=%s'
                      % (metier.replace(' ', '+'), contrat, limit_date))
        assert self.is_on_page(SearchPage)
        return self.page.iter_job_adverts()

    @id2url(IndeedJobAdvert.id2url)
    def get_job_advert(self, url, advert):
        self.location(url)
        assert self.is_on_page(AdvertPage)
        return self.page.get_job_advert(url, advert)
