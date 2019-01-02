# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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
from weboob.tools.value import Value
from weboob.capabilities.video import BaseVideo
from .video import SITE


class ArteTest(BackendTest):
    MODULE = 'arte'

    def setUp(self):
        if not self.is_backend_configured():
            self.backend.config['lang'] = Value(value='FRENCH')
            self.backend.config['quality'] = Value(value='HD')
            self.backend.config['order'] = Value(value='LAST_CHANCE')
            self.backend.config['format'] = Value(value='HLS')
            self.backend.config['version'] = Value(value='VOSTF')

    def test_search(self):
        l = list(zip(self.backend.search_videos('a'), range(30)))
        assert len(l)
        v = l[0][0]
        self.backend.fillobj(v, ('url',))
        self.assertTrue(v.url, 'URL for video "%s" not found' % (v.id))

    def test_sites(self):
        for site in SITE.values:

            l1 = list(self.backend.iter_resources([BaseVideo], [site.get('id')]))
            assert len(l1)

            while not isinstance(l1[0], BaseVideo):
                l1 = list(self.backend.iter_resources([BaseVideo], l1[-1].split_path))
                assert len(l1)

            for v in l1:
                v = self.backend.fillobj(v, ('url',))
                if type(v) == BaseVideo:
                    exit

            self.assertTrue(v.url, 'URL for video "%s" not found' % (v.id))
