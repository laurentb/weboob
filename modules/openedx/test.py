# -*- coding: utf-8 -*-

# Copyright(C) 2016      Simon Lipp
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


class OpenEDXTest(BackendTest):
    MODULE = 'openedx'

    def test_openedx(self):
        thread = next(self.backend.iter_threads())
        thread = self.backend.get_thread(thread.id)
        self.assertTrue(thread.id)
        self.assertTrue(thread.title)
        self.assertTrue(thread.url)
        self.assertTrue(thread.root.id)
        self.assertTrue(thread.root.content)
        self.assertTrue(thread.root.children)
        self.assertTrue(thread.root.url)
        self.assertTrue(thread.root.date)
