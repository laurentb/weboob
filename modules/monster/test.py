# -*- coding: utf-8 -*-

# Copyright(C) 2013      Bezleputh
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


class MonsterTest(BackendTest):
    MODULE = 'monster'

    def test_monster_search(self):
        l = list(itertools.islice(self.backend.search_job(u'marketing'), 0, 20))
        assert len(l)
        advert = self.backend.get_job_advert(l[0].id, None)
        self.assertTrue(advert.url, 'URL for announce "%s" not found: %s' % (advert.id, advert.url))

    def test_monster_advanced_search(self):
        l = list(itertools.islice(self.backend.advanced_search_job(), 0, 20))
        assert len(l)
        advert = self.backend.get_job_advert(l[0].id, None)
        self.assertTrue(advert.url, 'URL for announce "%s" not found: %s' % (advert.id, advert.url))
