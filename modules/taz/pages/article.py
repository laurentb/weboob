"ArticlePage object for Taz newspaper"
# -*- coding: utf-8 -*-

# Copyright(C) 2012 Florent Fourcot
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


class ArticlePage(GenericNewsPage):
    "ArticlePage object for taz"

    def on_loaded(self):
        self.main_div = self.document.getroot()
        self.element_title_selector = "title"
        self.element_author_selector = ".content-author>a"

    def get_body(self):
        div = self.document.getroot().find('.//div[@class="sectbody"]')
        for a in div.findall('.//a'):
            try:
                if a.attrib["href"][0:7] != "http://":
                    a.attrib["href"] = "http://taz.de/" + a.attrib["href"]
            except:
                continue
        for img in div.findall('.//img'):
            if img.attrib["src"][0:7] != "http://":
                img.attrib["src"] = "http://taz.de/" + img.attrib["src"]

        return self.parser.tostring(div)

    def get_title(self):
        title = GenericNewsPage.get_title(self)
        return title

    def get_author(self):
        author = self.document.getroot().xpath('//span[@class="author"]')
        if author:
            return author[0].text.replace('von ', '')
