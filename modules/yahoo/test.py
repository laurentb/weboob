# -*- coding: utf-8 -*-

# Copyright(C) 2011  Romain Bignon
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


from weboob.tools.test import BackendTest


class YahooTest(BackendTest):
    MODULE = 'yahoo'

    def test_meteo(self):
        l = list(self.backend.iter_city_search('paris'))
        self.assertTrue(len(l) > 0)

        city = l[0]
        current = self.backend.get_current(city.id)

        self.assertTrue(current.temp.unit in ['C', 'F'])

        if current.temp.unit == 'F':
            self.assertTrue(current.temp.value > -4 and current.temp.value < 122)
        else:
            self.assertTrue(current.temp.value > -20 and current.temp.value < 50)

        forecasts = list(self.backend.iter_forecast(city.id))
        self.assertTrue(len(forecasts) > 0)
