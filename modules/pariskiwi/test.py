# -*- coding: utf-8 -*-

# Copyright(C) 2013      Vincent A
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


from weboob.tools.test import BackendTest
from datetime import datetime, date


class ParisKiwiTest(BackendTest):
    MODULE = 'pariskiwi'

    def test_pariskiwi_event(self):
        event = self.backend.get_event('11-9-2013_-Event_2')
        self.assertTrue(event)
        self.assertIn('Belleville', event.location)
        self.assertEqual(event.price, 5)
        self.assertTrue(event.summary)
        self.assertEqual(event.start_date, datetime(2013, 11, 9, 20, 30))
        self.assertEqual(event.url, 'https://pariskiwi.org/index.php/Agenda/Detruire_Ennui_Paris/11-9-2013_-Event_2')

    def test_pariskiwi_list(self):
        it = self.backend.list_events(datetime.now())
        ev = next(it)
        self.assertTrue(ev)
        self.assertGreaterEqual(ev.start_date.date(), date.today())
