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

from .pages import ListStationsPage, InfoStationPage


__all__ = ['VlilleBrowser']


class VlilleBrowser(BaseBrowser):
    PROTOCOL = 'http'
    DOMAIN = 'www.vlille.fr/stations'
    ENCODING = None

    PAGES = {
        '%s://%s/xml-station.aspx\?borne=.*' % (PROTOCOL, DOMAIN): InfoStationPage,
        '%s://%s/xml-stations.aspx' % (PROTOCOL, DOMAIN): ListStationsPage,
    }

    def get_station_list(self):
        if not self.is_on_page(ListStationsPage):
            self.location(u'%s://%s/xml-stations.aspx' % (self.PROTOCOL, self.DOMAIN))
        return self.page.get_station_list()

    def get_station_infos(self, gauge):
        self.location('%s://%s/xml-station.aspx?borne=%s' % (self.PROTOCOL, self.DOMAIN, gauge.id))
        return self.page.get_station_infos(gauge.id)
