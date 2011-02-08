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
from .minutes20 import Minutes20Page, NoAuthorElement

class ArticlePage(Minutes20Page):
    def set_body(self):
        self.element_body = select(self.main_div, "div.mna-body", 1) 
        self.element_body.remove(select(self.element_body, "div.mna-tools", 1))
        try:
            self.element_body.remove(select(self.element_body, "div.mna-comment-call", 1))
        except SelectElementException:
            pass
        try:
            self.element_body.remove(self.get_element_author())
        except NoAuthorElement:
            pass
        self.article.body = self.browser.parser.tostring(self.element_body) 
