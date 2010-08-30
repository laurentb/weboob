# -*- coding: utf-8 -*-

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

from weboob.tools.browser import BaseBrowser

from .pages.board import BoardPage

class FourChan(BaseBrowser):
    DOMAIN = 'boards.4chan.org'
    PAGES = {'http://boards.4chan.org/\w+/': BoardPage,
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
