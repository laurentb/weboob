# -*- coding: utf-8 -*-

# Copyright(C) 2011-2012  Romain Bignon, Laurent Bachelier
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
from weboob.capabilities.video import BaseVideo
from weboob.capabilities.radio import Radio


class RadioFranceTest(BackendTest):
    MODULE = 'radiofrance'

    def test_get_radios(self):
        l = list(self.backend.iter_resources(objs=[Radio], split_path=[]))
        self.assertTrue(0 < len(l) < 30)
        for radio in l:
            name = radio.split_path[-1]
            if name != 'francebleu':
                streams = self.backend.get_radio(name).streams
                self.assertTrue(len(streams) > 0)

        l = list(self.backend.iter_resources(objs=[Radio], split_path=['francebleu']))
        self.assertTrue(len(l) > 30)

        for radio in l:
            streams = self.backend.get_radio(radio.split_path[-1]).streams
            self.assertTrue(len(streams) > 0)

        l = list(self.backend.iter_resources(objs=[BaseVideo], split_path=[]))
        self.assertEquals(len(l), 0)
