"ArticlePage object for minutes20"
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

from weboob.tools.capabilities.messages.genericArticle import NoAuthorElement, try_remove, NoneMainDiv
from .simple import SimplePage


class ArticlePage(SimplePage):
    "ArticlePage object for minutes20"

    def on_loaded(self):
        self.main_div = self.document.getroot()
        self.element_title_selector = "h1"
        self.element_author_selector = "div.mna-signature"
        self.element_body_selector = "div[role=main], div.mna-body"

    def get_body(self):
        try:
            element_body = self.get_element_body()
        except NoneMainDiv:
            return None
        else:
            try_remove(self.parser, element_body, "div.mna-tools")
            try_remove(self.parser, element_body, "div.mna-comment-call")
            try_remove(self.parser, element_body, "ul[class^=content-related]")
            try_remove(self.parser, element_body, "ul[class^=content-related]")
            try_remove(self.parser, element_body, "p.author-sign")
            try:
                element_body.remove(self.get_element_author())
            except NoAuthorElement:
                pass
            return self.parser.tostring(element_body)
