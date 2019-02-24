# -*- coding: utf-8 -*-

# Copyright(C) 2014      Vincent A
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

from base64 import b64decode

from weboob.tools.test import BackendTest


class PixtoilelibreTest(BackendTest):
    MODULE = 'pixtoilelibre'

    # small gif file
    DATA = 'R0lGODlhAQABAIAAAP///wAAACH5BAAAAAAALAAAAAABAAEAAAICRAEAOw==\n'

    def test_pixtoilelibre(self):
        assert self.backend.can_post(self.DATA, max_age=0)

        post = self.backend.new_paste(None)
        post.contents = self.DATA
        post.public = True
        self.backend.post_paste(post, max_age=0)
        assert post.id

        got = self.backend.get_paste(post.id)
        assert got
        self.assertEquals(b64decode(got.contents), b64decode(self.DATA))
