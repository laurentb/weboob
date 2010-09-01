# -*- CODing: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


from weboob.tools.test import BackendTest


__all__ = ['AuMTest']


class AuMTest(BackendTest):
    BACKEND = 'aum'

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
            self.backend.fillobj(contacts[0], ['photos', 'profile'])
        except BrowserUnavailable:
            # enough frequent to do not care about.
            pass
