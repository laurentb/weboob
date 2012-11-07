"ArticlePage object for presseurope"
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

from weboob.tools.capabilities.messages.genericArticle import GenericNewsPage, try_drop_tree


class PresseuropPage(GenericNewsPage):
    "PresseuropPage object for presseurop"

    def on_loaded(self):
        self.main_div = self.document.getroot()
        self.element_title_selector = "title"
        self.element_author_selector = "div[id=content-author]>a"
        self.element_body_selector = "div.block"

    def get_body(self):
        element_body = self.get_element_body()
        try_drop_tree(self.parser, element_body, "li.button-social")
        try_drop_tree(self.parser, element_body, "div.sharecount")

        return self.parser.tostring(element_body)

    def get_title(self):
        title = GenericNewsPage.get_title(self)
        title = title.split('|')[0]
        return title


class CartoonPage(PresseuropPage):
    "CartoonPage object for presseurop"

    def on_loaded(self):
        self.main_div = self.document.getroot()
        self.element_title_selector = "title"
        self.element_author_selector = "div.profilecartoontext>p>a"
        self.element_body_selector = "div.panel"
