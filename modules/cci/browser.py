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
from weboob.capabilities.job import BaseJobAdvert

from .pages import SearchPage


__all__ = ['CciBrowser']


class CciBrowser(PagesBrowser):
    BASEURL = 'http://www.cci.fr'

    search_page = URL('/web/recrutement/les-offres-d-emploi', SearchPage)

    def search_job(self, pattern):
        return self.search_page.go().iter_job_adverts(pattern=pattern)

    def get_job_advert(self, _id, advert):
        if advert is None:
            advert = BaseJobAdvert(_id)
        return self.search_page.stay_or_go().get_job_advert(obj=advert)
