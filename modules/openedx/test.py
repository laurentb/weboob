# -*- coding: utf-8 -*-

# Copyright(C) 2016      Simon Lipp
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


from weboob.tools.test import BackendTest, skip_without_config


class OpenEDXTest(BackendTest):
    MODULE = 'openedx'

    @skip_without_config('username', 'password')
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
