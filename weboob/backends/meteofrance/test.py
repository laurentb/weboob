# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


from weboob.tools.test import BackendTest

class MeteoFranceTest(BackendTest):
    BACKEND = 'meteofrance'

    def test_meteofrance(self):
        l = list(self.backend.iter_city_search('paris'))
        self.assertTrue(len(l) > 0)

        city = l[0]
        current = self.backend.get_current(city.id)
        self.assertTrue(current.temp > -20 and current.temp < 50)

        forecasts = list(self.backend.iter_forecast(city.id))
        self.assertTrue(len(forecasts) > 0)
