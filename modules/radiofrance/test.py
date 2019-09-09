# -*- coding: utf-8 -*-

# Copyright(C) 2011-2012  Romain Bignon, Laurent Bachelier
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
from weboob.capabilities.audio import BaseAudio
from weboob.capabilities.radio import Radio
import itertools


class RadioFranceTest(BackendTest):
    MODULE = 'radiofrance'

    def test_ls_radios_and_selections(self):
        l = list(self.backend.iter_resources(objs=[Radio], split_path=[]))

        self.assertTrue(0 < len(l) < 30)
        for radio in l:
            name = radio.split_path[-1]
            if name != 'francebleu':
                streams = self.backend.get_radio(name).streams
                self.assertTrue(len(streams) > 0)

                l_sel = list(self.backend.iter_resources(objs=[BaseAudio], split_path=[name, 'selection']))
                if len(l_sel) > 0:
                    self.assertTrue(len(l_sel[0].url) > 0)

        l = list(self.backend.iter_resources(objs=[Radio], split_path=['francebleu']))
        self.assertTrue(len(l) > 30)

        for radio in l:
            streams = self.backend.get_radio(radio.split_path[-1]).streams
            self.assertTrue(len(streams) > 0)

            l_sel1 = list(self.backend.iter_resources(objs=[BaseAudio],
                                                      split_path=['francebleu',
                                                                  radio.split_path[-1]]))

            if 'Selection' in [el.title for el in l_sel1]:
                l_sel = list(self.backend.iter_resources(objs=[BaseAudio],
                                                         split_path=['francebleu',
                                                                     radio.split_path[-1],
                                                                     'selection']))
                if len(l_sel) > 0:
                    self.assertTrue(len(l_sel[0].url) > 0)

    def test_podcasts(self):
        for key, item in self.backend._RADIOS.items():
            if 'podcast' in item:
                emissions = list(self.backend.iter_resources(objs=[BaseAudio], split_path=[key, 'podcasts']))
                self.assertTrue(len(emissions) > 0)
                podcasts = list(self.backend.iter_resources(objs=[BaseAudio], split_path=emissions[0].split_path))
                self.assertTrue(len(podcasts) > 0)
                podcast = self.backend.get_audio(podcasts[0].id)
                self.assertTrue(podcast.url)

    def test_search_radio(self):
        l = list(self.backend.iter_radios_search('bleu'))
        self.assertTrue(len(l) > 0)
        self.assertTrue(len(l[0].streams) > 0)

    def test_search_get_audio(self):
        l = list(itertools.islice(self.backend.search_audio('jou'), 0, 20))
        self.assertTrue(len(l) > 0)

        a = self.backend.get_audio(l[0].id)
        self.assertTrue(a.url)
