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

from weboob.tools.parsers.lxmlparser import select
from weboob.tools.genericArticle import GenericNewsPage, try_remove, \
                                        try_remove_from_selector_list

class ArticlePage(GenericNewsPage):
    "ArticlePage object for inrocks"
    def on_loaded(self):
        self.main_div = self.document.getroot()
        self.element_title_selector = "h1"
        self.element_author_selector    = "div.name>span"
        self.element_body_selector      = "div.maincol"

    def get_body(self):
        element_body = self.get_element_body()
        try_remove(element_body, "div.sidebar")
        try_remove(select(element_body, "div.details", 1), "div.footer")
        try_remove_from_selector_list(select(element_body, "div.header", 1), 
                                      ["h1", "div.picture", "div.date", 
                                       "div.news-single-img", 
                                       "div.metas_img", "strong"])
        return self.browser.parser.tostring(element_body)


