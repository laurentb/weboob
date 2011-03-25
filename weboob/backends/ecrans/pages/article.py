"ArticlePage object for inrocks"
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

from weboob.tools.genericArticle import GenericNewsPage, remove_from_selector_list, try_remove_from_selector_list, try_drop_tree
class ArticlePage(GenericNewsPage):
    "ArticlePage object for inrocks"
    def on_loaded(self):
        self.main_div = self.document.getroot()
        self.element_title_selector = "h3"
        self.element_author_selector    = "p.auteur>a"
        self.element_body_selector      = "div.bloc_article_01"

    def get_body(self):
        element_body = self.get_element_body()
        remove_from_selector_list(element_body, [self.element_title_selector, "p.auteur", "h4", "h4"])
        try_remove_from_selector_list(element_body, ["p.tag", "div.alire"])
        try_drop_tree(element_body, "script")

        return self.browser.parser.tostring(element_body)

