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

from weboob.tools.browser.decorators import id2url
from weboob.tools.browser import BaseBrowser

from .pages import SearchPage, AdvertPage
from .job import ApecJobAdvert

__all__ = ['ApecBrowser']


class ApecBrowser(BaseBrowser):
    PROTOCOL = 'http'
    DOMAIN = 'www.apec.fr'
    ENCODING = None

    PAGES = {
        'http://cadres.apec.fr/MesOffres/RechercheOffres/ApecRechercheOffre.jsp\?keywords=(.*?)': SearchPage,
        'http://cadres.apec.fr/offres-emploi-cadres/offres-emploi-cadres/\d*_\d*_\d*_(.*?)________(.*?).html(.*?)': AdvertPage,
    }

    def search_job(self, pattern):
        if pattern is not None:
            self.location('http://cadres.apec.fr/MesOffres/RechercheOffres/ApecRechercheOffre.jsp?keywords=%s' % pattern.replace(' ','+'))
            assert self.is_on_page(SearchPage)
            return self.page.iter_job_adverts()
        else:
            return []

    @id2url(ApecJobAdvert.id2url)
    def get_job_advert(self, url, advert):
        self.location(url)
        assert self.is_on_page(AdvertPage)
        return self.page.get_job_advert(url, advert)
