# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
# Copyright(C) 2012 François Revol
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

from weboob.capabilities.video import BaseVideo
from weboob.tools.test import BackendTest
import itertools


class VimeoTest(BackendTest):
    MODULE = 'vimeo'

    def test_search(self):
        l = list(itertools.islice(self.backend.search_videos('boobs'), 0, 20))
        self.assertTrue(len(l) > 0)
        v = l[0]
        self.backend.fillobj(v, ('url',))
        self.assertTrue(v.url and v.url.startswith('http://'), 'URL for video "%s" not found: %s' % (v.id, v.url))

    def test_channels(self):
        l = list(itertools.islice(self.backend.iter_resources([BaseVideo], [u'vimeo-channels']), 0, 20))
        self.assertTrue(len(l) > 0)
        l1 = list(itertools.islice(self.backend.iter_resources([BaseVideo], l[0].split_path), 0, 20))
        self.assertTrue(len(l1) > 0)
        v = l1[0]
        self.backend.fillobj(v, ('url',))
        self.assertTrue(v.url and v.url.startswith('http://'), 'URL for video "%s" not found: %s' % (v.id, v.url))

    def test_categories(self):
        l = list(itertools.islice(self.backend.iter_resources([BaseVideo], [u'vimeo-categories']), 0, 20))
        self.assertTrue(len(l) > 0)
        l1 = list(itertools.islice(self.backend.iter_resources([BaseVideo], l[0].split_path), 0, 20))
        self.assertTrue(len(l1) > 0)
        v = l1[0]
        self.backend.fillobj(v, ('url',))
        self.assertTrue(v.url and v.url.startswith('http://'), 'URL for video "%s" not found: %s' % (v.id, v.url))
