# -*- coding: utf-8 -*-

# Copyright(C) 2011  Julien Hebert
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

from .pages.article import ArticlePage
from .pages.simple import SimplePage
from weboob.tools.browser import BaseBrowser
from .tools import id2url


class Newspaper20minutesBrowser(BaseBrowser):
    PAGES = {
             'http://www.20minutes.fr/article/?.*': ArticlePage,
             'http://www.20minutes.fr/ledirect/?.*': SimplePage,
             'http://www.20minutes.fr/preums/?.*': SimplePage
            }

    def is_logged(self):
        return False

    def get_content(self, _id):
        try :
            url = id2url(_id)
        except ValueError:
            url = _id
        try:
            self.location(url)
        except IndexError:
            if _id == '':
                raise ValueError("thread id is empty")
            else:
                raise
        return self.page.get_article(_id)
