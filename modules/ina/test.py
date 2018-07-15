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

import itertools
from weboob.tools.test import BackendTest


class INATest(BackendTest):
    MODULE = 'ina'

    def test_video_ina(self):
        l = list(itertools.islice(self.backend.search_videos('sarkozy'), 0, 20))
        self.assertTrue(len(l) > 0)
        v_id = l[0].id
        v = self.backend.get_video(v_id)
        self.assertTrue(v.url and v.url.startswith('https://'), 'URL for video "%s" not found: %s' % (v.id, v.url))

    def test_audio_ina(self):
        l = list(itertools.islice(self.backend.search_audio('sarkozy'), 0, 20))
        self.assertTrue(len(l) > 0)
        a_id = l[0].id
        a = self.backend.get_audio(a_id)
        self.assertTrue(a.url and a.url.startswith('https://'), 'URL for video "%s" not found: %s' % (a.id, a.url))
