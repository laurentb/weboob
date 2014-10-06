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


from weboob.browser import PagesBrowser, URL

from .pages import ListStationsPage, InfoStationPage


__all__ = ['VlilleBrowser']


class VlilleBrowser(PagesBrowser):

    BASEURL = 'http://www.vlille.fr'
    list_page = URL('/stations/les-stations-vlille.aspx', ListStationsPage)
    info_page = URL('/stations/xml-station.aspx\?borne=(?P<idgauge>.*)', InfoStationPage)

    def get_station_list(self):
        return self.list_page.go().get_station_list()

    def get_station_infos(self, gauge):
        return self.info_page.go(idgauge=gauge.id).get_station_infos(obj=gauge)
