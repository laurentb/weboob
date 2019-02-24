# -*- coding: utf-8 -*-

# Copyright(C) 2015      Vincent A
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


class LutimTest(BackendTest):
    MODULE = 'lutim'

    # small gif file
    DATA = u'R0lGODlhAQABAPAAAP///wAAACH5BAAAAAAALAAAAAABAAEAAAICRAEAOw==\n'
    TITLE = u'foo.gif'

    def test_lutim(self):
        post = self.backend.new_paste(None)
        post.contents = self.DATA
        post.title = self.TITLE
        assert self.backend.can_post(post.contents, post.title)
        self.backend.post_paste(post, max_age=86400)
        self.assertTrue(post.id)

        got = self.backend.get_paste(post.id)
        self.assertTrue(got)
        self.assertEqual(got.title, self.TITLE)
        self.assertEqual(got.contents.strip(), self.DATA.strip())

        # test with an empty name
        post.title = u''
        self.backend.post_paste(post, max_age=86400)

    def test_invalid(self):
        post = self.backend.new_paste(None)
        post.contents = u'FAIL'
        post.title = self.TITLE

        assert not self.backend.can_post(post.contents, post.title)
