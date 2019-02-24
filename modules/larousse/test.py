# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from weboob.tools.test import BackendTest


class LarousseTest(BackendTest):
    MODULE = 'larousse'

    def _check_translations(self, src, dst, text):
        res = list(self.backend.translate(src, dst, text))
        for trans in res:
            self.assertEqual(trans.lang_src, src)
            self.assertEqual(trans.lang_dst, dst)
        return [t.text for t in res]

    def test_translate(self):
        res = self._check_translations('French', 'English', 'maison')
        assert res
        assert any(t == 'house' for t in res)

        res = self._check_translations('German', 'French', 'kaffee')
        assert res
        assert any('café' in t for t in res)
