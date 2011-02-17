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
from .inrocks import InrocksPage

def try_remove(base_element, selector):
    try :
        base_element.remove(select(base_element, selector, 1 ))
    except (SelectElementException, ValueError):
        pass

class ArticlePage(InrocksPage):
    def set_body(self):
        self.element_body = select(self.main_div, "div.maincol", 1)
        try_remove(self.element_body, "div.sidebar")
        details = select(self.element_body, "div.details", 1)
        try_remove(details, "div.footer")
        header = select(self.element_body, "div.header", 1)
        for selector in ["h1", "div.picture", "div.date", "div.news-single-img", 
                         "div.metas_img", "strong"]:
            try_remove(header, selector)

        self.article.body = self.browser.parser.tostring(self.element_body)
