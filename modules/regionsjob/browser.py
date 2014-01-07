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
import urllib

from weboob.tools.browser import BaseBrowser
from weboob.tools.browser.decorators import id2url

from .pages import SearchPage, AdvertPage
from .job import RegionsJobAdvert


__all__ = ['RegionsjobBrowser']


class RegionsjobBrowser(BaseBrowser):
    PROTOCOL = 'http'
    ENCODING = 'utf-8'

    PAGES = {
        '%s://(.*?)/offre_emploi/index.aspx\?v=___(.*?)_(.*?)_(.*?)_(.*?)_(.*?)_(.*?)_(.*?)_(.*?)_(.*?)_(.*?)_' % (PROTOCOL): SearchPage,
        '%s://(.*?)/offre_emploi/detailoffre.aspx\?numoffre=(.*?)&de=consultation' % (PROTOCOL): AdvertPage,
    }

    def __init__(self, website, *args, **kwargs):
        self.DOMAIN = website
        BaseBrowser.__init__(self, *args, **kwargs)

    def search_job(self, pattern=''):
        self.location('%s://%s/offre_emploi/index.aspx?v=___0_0_0_0_0_0_0_0_0_%s_'
                      % (self.PROTOCOL, self.DOMAIN, urllib.quote_plus(pattern.encode(self.ENCODING))))
        assert self.is_on_page(SearchPage)
        return self.page.iter_job_adverts(self.DOMAIN)

    def advanced_search_job(self, metier, fonction, secteur, contract, experience):
        self.location('%s://%s/offre_emploi/index.aspx?v=___%s_%s_%s_%s_%s_%s_%s_%s_%s_%s_'
                      % (self.PROTOCOL,
                         self.DOMAIN,
                         '0',
                         fonction,
                         experience,
                         '0',
                         contract,
                         '0',
                         '0',
                         secteur,
                         '0',
                         urllib.quote_plus(metier.encode(self.ENCODING))))
        assert self.is_on_page(SearchPage)
        return self.page.iter_job_adverts(self.DOMAIN)

    @id2url(RegionsJobAdvert.id2url)
    def get_job_advert(self, url, advert):
        self.location(url)
        assert self.is_on_page(AdvertPage)
        return self.page.get_job_advert(url, advert)
