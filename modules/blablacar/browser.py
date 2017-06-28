# -*- coding: utf-8 -*-

# Copyright(C) 2015      Bezleputh
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
from weboob.tools.compat import urlencode

from .pages import DeparturesPage

from datetime import datetime


class BlablacarBrowser(PagesBrowser):
    BASEURL = 'https://www.blablacar.fr'

    departures = URL('/search_xhr\?(?P<qry>.*)', DeparturesPage)

    def get_roadmap(self, departure, arrival, filters):
        pass

    def get_station_departures(self, station_id, arrival_id, date):
        query = {'fn': station_id}
        if arrival_id:
            query['tn'] = arrival_id

            if date:
                _date = datetime.strftime(date, "%d/%m/%Y")
                query['db'] = _date
                _heure = datetime.strftime(date, "%H")
                query['hb'] = _heure
                query['he'] = '24'

        return self.departures.open(qry=urlencode(query)).get_station_departures()
