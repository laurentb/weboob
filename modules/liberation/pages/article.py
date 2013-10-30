# -*- coding: utf-8 -*-

# Copyright(C) 2013 Florent Fourcot
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

from weboob.tools.capabilities.messages.genericArticle import GenericNewsPage,\
    NoBodyElement, NoAuthorElement, NoneMainDiv


class ArticlePage(GenericNewsPage):
    "ArticlePage object for Libe"

    def on_loaded(self):
        self.main_div = self.document.getroot()
        self.element_title_selector = "title"
        self.element_author_selector = "span.author"
        self.element_body_selector = "div.article-body"

    def get_body(self):
        if '.blogs.liberation.fr/' in self.url:
            self.element_body_selector = "div.entry-content"
        try:
            return self.parser.tostring(self.get_element_body())
        except NoBodyElement:
            meta = self.document.xpath('//meta[@name="description"]')[0]
            txt = meta.attrib['content']
            return txt

    def get_title(self):
        title = GenericNewsPage.get_title(self)
        return title.replace(u' - Libération', '')

    def get_author(self):
        try:
            author = self.get_element_author().text_content().strip()
            if author.startswith('Par '):
                return author.split('Par ', 1)[1]
            else:
                return author
        except (NoAuthorElement, NoneMainDiv):
            #TODO: Mettre un warning
            return None
