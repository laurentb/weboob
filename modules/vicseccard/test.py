# -*- coding: utf-8 -*-

# Copyright(C) 2015      Oleg Plakhotniuk
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
from itertools import chain


class VicSecCardTest(BackendTest):
    MODULE = 'vicseccard'

    def test_history(self):
        """
        Test that there's at least one transaction in the whole history.
        """
        b = self.backend
        ts = chain(*[b.iter_history(a) for a in b.iter_accounts()])
        t = next(ts, None)
        self.assertNotEqual(t, None)
