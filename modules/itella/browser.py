# -*- coding: utf-8 -*-

# Copyright(C) 2015      Matthieu Weber
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


from weboob.browser import PagesBrowser, URL

from .pages import SearchPage


class ItellaBrowser(PagesBrowser):
    BASEURL = 'http://www.itella.fi'

    search_page = URL('/itemtracking/itella/search_by_shipment_id\?lang=en&ShipmentId=(?P<id>.+)', SearchPage)

    def get_tracking_info(self, _id):
        return self.search_page.go(id=_id).get_info(_id)
