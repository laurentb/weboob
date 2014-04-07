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

from weboob.tools.browser2 import PagesBrowser, URL

from .pages import SearchPage, AdvertPage

__all__ = ['RegionsjobBrowser']


class RegionsjobBrowser(PagesBrowser):

    advert_page = URL('/offre_emploi/detailoffre.aspx\?numoffre=(?P<_id>.*)&de=consultation', AdvertPage)
    search_page = URL('/offre_emploi/index.aspx\?v=___0_(?P<fonction>.*)_(?P<experience>.*)_0_(?P<contract>.*)_0_0_(?P<secteur>.*)_0_(?P<metier>.*)_', SearchPage)

    def __init__(self, website, *args, **kwargs):
        self.BASEURL = 'http://%s' % website
        PagesBrowser.__init__(self, *args, **kwargs)

    def search_job(self, pattern='', fonction=0, secteur=0, contract=0, experience=0):
        return self.search_page.go(fonction=fonction,
                                   experience=experience,
                                   contract=contract,
                                   secteur=secteur,
                                   metier=urllib.quote_plus(pattern.encode('utf-8'))
                                   ).iter_job_adverts(domain=self.BASEURL)

    def get_job_advert(self, _id, advert):
        splitted_id = _id.split('#')
        self.BASEURL = splitted_id[0]
        return self.advert_page.go(_id=splitted_id[1]).get_job_advert(obj=advert)
