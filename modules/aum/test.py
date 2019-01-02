# -*- CODing: utf-8 -*-

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


from weboob.tools.test import BackendTest
from weboob.exceptions import BrowserUnavailable


class AuMTest(BackendTest):
    MODULE = 'aum'

    def test_new_messages(self):
        try:
            for message in self.backend.iter_unread_messages():
                pass
        except BrowserUnavailable:
            # enough frequent to do not care about.
            pass

    def test_contacts(self):
        try:
            contacts = list(self.backend.iter_contacts())
            if len(contacts) == 0:
                # so bad, we can't test that...
                return
            self.backend.fillobj(contacts[0], ['photos', 'profile'])
        except BrowserUnavailable:
            # enough frequent to do not care about.
            pass
