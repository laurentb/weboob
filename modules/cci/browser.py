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

from .pages import SearchPage


__all__ = ['CciBrowser']


class CciBrowser(BaseBrowser):
    PROTOCOL = 'http'
    DOMAIN = 'www.cci.fr/web/recrutement/les-offres-d-emploi'
    ENCODING = "UTF-8"

    PAGES = {
        '%s://%s' % (PROTOCOL, DOMAIN): SearchPage,
    }

    def search_job(self, pattern):
        self.location('%s://%s' % (self.PROTOCOL, self.DOMAIN))
        assert self.is_on_page(SearchPage)
        return self.page.iter_job_adverts(pattern)

    def get_job_advert(self, _id, advert):
        self.location('%s://%s' % (self.PROTOCOL, self.DOMAIN))
        assert self.is_on_page(SearchPage)
        return self.page.get_job_advert(_id, advert)
