# -*- coding: utf-8 -*-

# Copyright(C) 2015 Matthieu Weber
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


from weboob.tools.test import BackendTest


class IlmatieteenlaitosTest(BackendTest):
    MODULE = 'ilmatieteenlaitos'

    def test_ilmatieteenlaitos(self):
        l = list(self.backend.iter_city_search('helsinki'))
        self.assertTrue(len(l) > 0)

        city = l[0]
        current = self.backend.get_current(city.id)
        self.assertTrue(current.temp.value > -50 and current.temp.value < 50)

        forecasts = list(self.backend.iter_forecast(city.id))
        self.assertTrue(len(forecasts) > 0)
