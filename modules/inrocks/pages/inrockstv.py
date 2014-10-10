"ArticlePage object for inrocks"
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

from weboob.tools.capabilities.messages.genericArticle import GenericNewsPage


class InrocksTvPage(GenericNewsPage):
    "ArticlePage object for inrocks"

    def on_loaded(self):
        self.main_div = self.document.getroot()
        self.element_title_selector = "h2"
        self.element_author_selector    = "div.name>span"
        self.element_body_selector      = "span.infos"

    def get_body(self):
        element_body = self.get_element_body()
        return self.parser.tostring(element_body)
