# -*- coding: utf-8 -*-

# Copyright(C) 2016      Vincent A
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

from base64 import b64decode

from weboob.tools.test import BackendTest


class ImgurTest(BackendTest):
    MODULE = 'imgur'

    # small gif file
    DATA = 'R0lGODdhAQABAPAAAP///wAAACwAAAAAAQABAAACAkQBADs=\n'

    def test_post(self):
        assert self.backend.can_post(self.DATA, max_age=0)

        post = self.backend.new_paste(None)
        post.contents = self.DATA
        post.public = True
        self.backend.post_paste(post, max_age=0)
        assert post.id

        got = self.backend.get_paste(post.id)
        assert got
        assert b64decode(got.contents) == b64decode(self.DATA)

    def test_search(self):
        it = iter(self.backend.search_image('lol'))
        img = next(it)
        assert img

        it = iter(self.backend.search_galleries('lol'))
        gall = next(it)
        assert gall
