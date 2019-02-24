# -*- coding: utf-8 -*-

# Copyright(C) 2013 Florent Fourcot
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

from weboob.tools.test import BackendTest, skip_without_config


class DresdenWetterTest(BackendTest):
    MODULE = 'dresdenwetter'

    @skip_without_config()
    def test_gauges_sensors(self):
        """
        test if the gauge listing works.
        Only one gauge on the website, but we can test sensors after that
        """
        l = list(self.backend.iter_gauges())
        self.assertTrue(len(l) == 1, msg="Gauge not found")
        self.assertTrue(len(l[0].sensors) > 5, msg="Not enough sensors")

    @skip_without_config()
    def test_sensors_value(self):
        temperature = self.backend.get_last_measure("dd-Temperatur2m").level
        self.assertTrue(temperature > -50., msg="To cold")
        self.assertTrue(temperature < 50., msg="Temperature to high")
        self.assertTrue(self.backend.get_last_measure(u"dd-Wind10minØ").level >= 0)
        self.assertTrue(self.backend.get_last_measure("dd-RelLuftdruck").level > 800.)
        self.assertTrue(self.backend.get_last_measure("dd-RelLuftfeuchtigkeit").level >= 0.)
        self.assertTrue(self.backend.get_last_measure("dd-Niederschlagseit001Uhr").level >= 0.)
        self.assertTrue(self.backend.get_last_measure("dd-Globalstrahlung").level >= 0.)

    @skip_without_config()
    def test_temperature(self):
        """
        test the first sensor return by module"
        """
        temperature = list(self.backend.iter_sensors("wetter", "Temperatur"))
        assert temperature[0].name == u"Temperatur 2m"
        assert temperature[0].unit == u"°C"

    @skip_without_config()
    def test_globalstrahlung(self):
        """
        Test the last sensor return by module"
        """
        sensor = list(self.backend.iter_sensors("wetter", "Globalstrahlung"))
        assert sensor[0].unit == u"W/m²"
