# -*- coding: utf-8 -*-

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


from weboob.deprecated.browser import Browser

from .pages.board import BoardPage


class FourChan(Browser):
    DOMAIN = 'boards.4chan.org'
    PAGES = {
        'http://boards.4chan.org/\w+/': BoardPage,
        'http://boards.4chan.org/\w+/res/\d+': BoardPage,
        }

    def is_logged(self):
        return True

    def get_threads(self, board):
        self.location('http://boards.4chan.org/%s/' % board)
        return self.page.articles

    def get_thread(self, board, id):
        self.location('http://boards.4chan.org/%s/res/%d' % (board, long(id)))
        assert len(self.page.articles) == 1
        return self.page.articles[0]
