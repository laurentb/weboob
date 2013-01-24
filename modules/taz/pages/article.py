"ArticlePage object for Taz newspaper"
# -*- coding: utf-8 -*-

# Copyright(C) 2012 Florent Fourcot
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

from weboob.tools.capabilities.messages.genericArticle import GenericNewsPage,\
        try_drop_tree, clean_relativ_urls


class ArticlePage(GenericNewsPage):
    "ArticlePage object for taz"

    def on_loaded(self):
        self.main_div = self.document.getroot()
        self.element_title_selector = "title"
        self.element_author_selector = ".content-author>a"

    def get_body(self):
        div = self.document.getroot().find('.//div[@class="sectbody"]')
        try_drop_tree(self.parser, div, "div.anchor")
        clean_relativ_urls(div, "http://taz.de")

        return self.parser.tostring(div)

    def get_title(self):
        title = GenericNewsPage.get_title(self)
        return title

    def get_author(self):
        author = self.document.getroot().xpath('//span[@class="author"]')
        if author:
            return author[0].text.replace('von ', '')
