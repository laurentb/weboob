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
from weboob.capabilities.video import BaseVideo
from .video import SITE


class ArteTest(BackendTest):
    MODULE = 'arte'

    def test_search(self):
        l = list(self.backend.search_videos('a'))
        assert len(l)
        v = l[0]
        self.backend.fillobj(v, ('url',))
        self.assertTrue(v.url, 'URL for video "%s" not found' % (v.id))

    def test_sites(self):
        for site in SITE.values:

            if site.get('id') == SITE.PROGRAM.get('id'):
                continue

            l1 = list(self.backend.iter_resources([BaseVideo], [site.get('id')]))
            assert len(l1)
            l1 = l1[0]

            while not isinstance(l1, BaseVideo):
                l1 = list(self.backend.iter_resources([BaseVideo], l1.split_path))
                assert len(l1)
                l1 = l1[0]

            self.backend.fillobj(l1, ('url',))
            self.assertTrue(l1.url, 'URL for video "%s" not found' % (l1.id))

    def test_latest(self):
        l = list(self.backend.iter_resources([BaseVideo], [u'arte-latest']))
        assert len(l)
        v = l[0]
        self.backend.fillobj(v, ('url',))
        self.assertTrue(v.url, 'URL for video "%s" not found' % (v.id))

    def test_program(self):
        l1 = list(self.backend.iter_resources([BaseVideo], [u'program']))
        assert len(l1)
        # some categories may contain no available videos (during summer period for example)
        for l in l1:
            l2 = list(self.backend.iter_resources([BaseVideo], l.split_path))
            if len(l2) == 0:
                continue

            break

        assert len(l2)
        v = l2[0]
        self.backend.fillobj(v, ('url',))
        self.assertTrue(v.url, 'URL for video "%s" not found' % (v.id))
