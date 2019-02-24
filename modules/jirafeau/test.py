# -*- coding: utf-8 -*-

# Copyright(C) 2016      Vincent A
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

import os

from weboob.tools.capabilities.paste import bin_to_b64
from weboob.tools.test import BackendTest


class JirafeauTest(BackendTest):
    MODULE = 'jirafeau'

    def test_jirafeau(self):
        data = os.urandom(1 << 10)

        assert self.backend.can_post(bin_to_b64(data), title='yeah.random', max_age=60)
        assert self.backend.can_post(bin_to_b64(data), title='yeah.random', max_age=60, public=False)
        assert not self.backend.can_post(bin_to_b64(data), title='yeah.random', max_age=60, public=True)
        assert not self.backend.can_post(bin_to_b64(data), title='yeah.random', max_age=False)

        paste = self.backend.new_paste(None, contents=bin_to_b64(data), title='yeah.random')
        self.backend.post_paste(paste, max_age=60)
        self.assertTrue(paste.id)
        self.assertTrue(paste.page_url)

        fetched = self.backend.get_paste(paste.url)
        self.assertTrue(fetched)
        self.assertEqual(fetched.id, paste.id)

        fetched = self.backend.get_paste(paste.id)
        self.assertTrue(fetched)
        self.backend.fillobj(fetched, 'contents')
        self.assertTrue(fetched.contents)
        assert fetched.contents == bin_to_b64(data)
