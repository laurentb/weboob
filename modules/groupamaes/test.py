# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from weboob.tools.test import BackendTest


class GroupamaesTest(BackendTest):
    MODULE = 'groupamaes'

    def test_groupamaes(self):
        l = list(self.backend.iter_accounts())
        if len(l) > 0:
            a = l[0]
            self.assertTrue(self.backend.get_account(l[0].id) is not None)
            list(self.backend.iter_history(a))
            list(self.backend.iter_investment(a))
