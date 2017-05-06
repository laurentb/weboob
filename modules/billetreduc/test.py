# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from __future__ import unicode_literals


from weboob.capabilities.base import empty
from weboob.capabilities.calendar import Query
from weboob.tools.test import BackendTest


class BilletreducTest(BackendTest):
    MODULE = 'billetreduc'

    def test_basic_search(self):
        q = Query()
        q.city = 'paris'

        event = None
        for n, event in enumerate(self.backend.search_events(q)):
            assert event.summary
            assert event.description
            assert event.start_date
            assert event.end_date
            assert event.start_date <= event.end_date
            assert event.city
            assert event.location
            assert not empty(event.price)
            assert event.category

            if n == 9:
                break
        else:
            assert False, 'not enough events'
