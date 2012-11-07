"ArticlePage object for ecrans"
# -*- coding: utf-8 -*-

# Copyright(C) 2011  Julien Hebert
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

from weboob.tools.capabilities.messages.genericArticle import GenericNewsPage, remove_from_selector_list, try_remove_from_selector_list, try_drop_tree, clean_relativ_urls


class ArticlePage(GenericNewsPage):
    "ArticlePage object for ecrans"
    def on_loaded(self):
        self.main_div = self.document.getroot()
        self.element_title_selector = "title"
        self.element_author_selector = "p.auteur>a"
        self.element_body_selector = "div.bloc_article_01"

    def get_body(self):
        element_body = self.get_element_body()
        remove_from_selector_list(self.parser, element_body, ["p.auteur", "h4"])
        try_remove_from_selector_list(self.parser, element_body, ["p.tag", "div.alire", self.element_title_selector, "h4"])
        try_drop_tree(self.parser, element_body, "script")
        clean_relativ_urls(element_body, "http://ecrans.fr")

        return self.parser.tostring(element_body)
