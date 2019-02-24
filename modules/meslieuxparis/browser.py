# -*- coding: utf-8 -*-

# Copyright(C) 2018      Vincent A
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

from __future__ import unicode_literals

from weboob.browser import PagesBrowser, URL

from .pages import ListPage


class MeslieuxparisBrowser(PagesBrowser):
    BASEURL = 'https://meslieux.paris.fr'

    list = URL(r'/proxy/data/get/equipements/get_equipements\?m_tid=(?P<equip>\d+)&limit=5000&order=name%20ASC&lat=48.8742&lon=2.38', ListPage)
    search = URL(r'/proxy/data/get/equipements/search_equipement\?cid=(?P<cid>[\d,]+)&limit=100', ListPage)

    # all categories can be found at https://meslieux.paris.fr/proxy/data/get/equipements/get_categories_equipement?id=all&type_name=search

    PARKS = [7, 14, 65, 91]
    POOLS = [27, 29]
    MARKETS = [289, 300]
    MUSEUMS = [67]
    HALLS = [100]
    SCHOOLS = [41, 43]

    ALL = [2, 5, 6, 7, 9, 14, 16, 17, 26, 27, 28, 30, 32, 36, 37, 39, 40, 41, 43,
           46, 47, 60, 62, 64, 65, 67, 70, 71, 76, 80, 82, 84, 85, 87, 91, 100,
           175, 177, 181, 235, 253, 267, 280, 287, 289, 290, 293, 300, 303,
          ]

    def search_contacts(self, pattern):
        ids = ','.join(str(id) for id in self.ALL)
        self.search.go(cid=ids, params={'keyword': pattern})
        for res in self.page.iter_contacts():
            yield res

