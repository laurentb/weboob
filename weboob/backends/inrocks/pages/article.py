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

from weboob.tools.parsers.lxmlparser import select, SelectElementException
from .genericArticle import GenericNewsPage

def try_remove(base_element, selector):
    try :
        base_element.remove(select(base_element, selector, 1 ))
    except (SelectElementException, ValueError):
        pass

class ArticlePage(GenericNewsPage):
    "ArticlePage object for inrocks"
    def on_loaded(self):
        self.main_div = self.document.getroot()
        self.element_author_selector    = "div.name>span"
        self.element_body_selector      = "div.maincol"

    def get_body(self):
        element_body = self.get_element_body()
        try_remove(element_body, "div.sidebar")
        details = select(element_body, "div.details", 1)
        try_remove(details, "div.footer")
        header = select(element_body, "div.header", 1)
        for selector in ["h1", "div.picture", "div.date", "div.news-single-img",
                         "div.metas_img", "strong"]:
            try_remove(header, selector)
        return self.browser.parser.tostring(element_body)


