"browser for inrocks.fr website"
# -*- coding: utf-8 -*-

# Copyright(C) 2011  Julien Hebert
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

from weboob.browser.url import URL
from .pages import GenericNewsPage
from weboob.browser import PagesBrowser


class GenericPageBrowser(PagesBrowser):
    generic_news_page = URL(GenericNewsPage)

    weboob = None

    def is_logged(self):
        return False

    def login(self):
        pass

    def fillobj(self, obj, fields):
        pass

    def get_content(self, _id):
        "return page article content"
        self.location(_id)
        if self.page is not None:
            return self.page.get_article(_id)
