# -*- coding: utf-8 -*-

# Copyright(C) 2011 Laurent Bachelier
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


from weboob.tools.browser import BaseBrowser

from .pages import PastePage, PostPage

__all__ = ['PastebinBrowser']

from weboob.tools.browser import BaseBrowser

class PastebinBrowser(BaseBrowser):
    DOMAIN = 'pastebin.com'
    ENCODING = 'UTF-8'
    PAGES = {'http://%s/(?P<id>.+)' % DOMAIN: PastePage,
            'http://%s/' % DOMAIN: PostPage}

    def fill_paste(self, paste):
        self.location(paste.page_url)
        return self.page.fill_paste(paste)

    def get_contents(self, _id):
        return self.readurl('http://%s/raw.php?i=%s' % (self.DOMAIN, _id))

    def post_paste(self, paste):
        self.home()
        self.page.post(paste)
        paste.id = self.page.get_id()
        self.fill_paste(paste)
