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
from weboob.tools.genericArticle import GenericNewsPage, try_remove

class ArticlePage(GenericNewsPage):
    "ArticlePage object for inrocks"
    def on_loaded(self):
        self.main_div = self.document.getroot()
        self.element_author_selector    = "div.name>span"
        self.element_title_selector     = "h1"
        self.element_body_selector      = "#article"

    def get_body(self):
        element_body    = self.get_element_body()
        h1_title        = select(element_body, self.element_title_selector, 1)
        div_infos       = select(element_body, "div.infos", 1)
        el_script       = select(element_body, "script", 1)

        element_body.remove(h1_title)
        element_body.remove(div_infos)
        element_body.remove(toolsbar)

        try_remove(element_body, "div.photo")
        try_remove(element_body, "div.art_bandeau_bottom")
        try_remove(element_body, "div.view")
        try_remove(element_body, "span.auteur_long")
        try_remove(element_body, "#toolsbar")

        el_script.drop_tree()
        element_body.find_class("texte")[0].drop_tag()
        element_body.tag = "div"
        return self.browser.parser.tostring(element_body)


