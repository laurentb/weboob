# -*- coding: utf-8 -*-

# Copyright(C) 2013      Vincent A
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
from datetime import datetime


class ParisKiwiTest(BackendTest):
    MODULE = 'pariskiwi'

    def test_pariskiwi_event(self):
        event = self.backend.get_event('11-9-2013_-Event_2')
        assert event
        assert event.location
        assert event.price
        assert event.summary
        assert event.url == 'http://pariskiwi.org/~parislagrise/mediawiki/index.php/Agenda/Detruire_Ennui_Paris/11-9-2013_-Event_2'
        assert event.start_date == datetime(2013, 11, 9, 20, 30)

    def test_pariskiwi_list(self):
        it = self.backend.list_events(datetime.now())
        ev = it.next()
        assert ev is not None
        assert ev.start_date >= datetime.now()
