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
        l = list(self.backend.iter_resources(objs=[Radio], split_path=['francebleu']))
        self.assertTrue(len(l) > 30)
        l = list(self.backend.iter_resources(objs=[BaseVideo], split_path=[]))
        self.assertEquals(len(l), 0)

    def test_get_video(self):
        # this should be available up to 24/10/2014 15h00
        urls = ('http://www.franceinter.fr/emission-vivre-avec-les-betes-y-arthus-bertrand-felins-g-tsai-s-envoler-conte-boreal-reha-hutin-30-m',
            'http://www.franceinter.fr/player/reecouter?play=263735',
            'franceinter-263735')
        for url in urls:
            vid = self.backend.get_video(url)
            assert vid.id == urls[-1]
        self.backend.fillobj(vid, ['url'])
        assert vid.url.lower().endswith('.mp3')

        # france culture (no expiration known)
        vid = self.backend.get_video('http://www.franceculture.fr/emission-la-dispute-expositions-paul-strand-youssef-nabil-et-dorothee-smith-2012-02-01')
        assert vid.id
        self.backend.fillobj(vid, ['url'])
        assert vid.url.lower().endswith('.mp3')

        # fip (no expiration known)
        # getting the proper ID is hard, hence the tests with many urls for the same content
        urls = ('http://www.fipradio.fr/diffusion-club-jazzafip-du-13-mars',
                'http://www.fipradio.fr/player/reecouter?play=20686',
            'fip-20686')
        for url in urls:
            vid = self.backend.get_video(url)
            assert vid.id == urls[-1]
        self.backend.fillobj(vid, ['url'])
        assert vid.url.lower().endswith('.mp3')
