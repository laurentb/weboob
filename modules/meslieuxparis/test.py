# -*- coding: utf-8 -*-

# Copyright(C) 2018      Vincent A
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

from __future__ import unicode_literals

from weboob.capabilities.contact import SearchQuery
from weboob.tools.test import BackendTest


class MeslieuxparisTest(BackendTest):
    MODULE = 'meslieuxparis'

    def test_search(self):
        q = SearchQuery()
        q.name = 'champ-de-mars' # site has no result for "champ de mars"...

        res = list(self.backend.search_contacts(q, None))
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].name, 'Parc du Champ-de-Mars')
        self.assertEqual(res[0].city, 'Paris')
        self.assertEqual(res[0].postcode, '75007')
        self.assertEqual(res[0].country, 'FR')
        self.assertEqual(res[0].address, '2 allée Adrienne-Lecouvreur')
        self.assertTrue(res[0].opening.is_open_now)

    def test_not(self):
        q = SearchQuery()
        q.name = 'champ de mars'
        q.city = 'marseille'

        res = list(self.backend.search_contacts(q, None))
        self.assertFalse(res)
