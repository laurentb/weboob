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


class MyHabitTest(BackendTest):
    MODULE = 'myhabit'

    def test_history(self):
        """
        Test that at least one item was ordered in the whole history.
        """
        b = self.backend
        items = (i for o in b.iter_orders() for i in b.iter_items(o))
        item = next(items, None)
        self.assertNotEqual(item, None)
