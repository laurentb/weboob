# -*- coding: utf-8 -*-

# Copyright(C) 2013 Roger Philibert
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
from weboob.capabilities.radio import Radio


class SomaFMTest(BackendTest):
    MODULE = 'somafm'

    def test_difm(self):
        ls = list(self.backend.iter_resources((Radio, ), []))
        self.assertTrue(len(ls) > 0)

        search = list(self.backend.iter_radios_search('doom'))
        self.assertTrue(len(search) > 0)
        self.assertTrue(len(search) < len(ls))

        radio = self.backend.get_radio('doomed')
        self.assertTrue(radio.title)
        self.assertTrue(radio.description)
        self.assertTrue(radio.current.who)
        self.assertTrue(radio.current.what)
        self.assertTrue(radio.streams[0].url)
        self.assertTrue(radio.streams[0].title)
