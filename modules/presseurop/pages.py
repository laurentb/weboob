"ArticlePage object for presseurope"
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

from weboob.browser.pages import AbstractPage
from weboob.browser.filters.html import CSS, CleanHTML


class PresseuropPage(AbstractPage):
    "PresseuropPage object for presseurop"
    _selector = CSS
    PARENT = 'genericnewspaper'
    PARENT_URL = 'generic_news_page'

    def on_loaded(self):
        self.main_div = self.doc.getroot()
        self.element_title_selector = "title"
        self.element_author_selector = "a[rel=author], div.profilecartoontext>p>a"
        self.element_body_selector = "div.block, div.panel, div.bodytext"

    def get_body(self):
        element_body = self.get_element_body()
        self.try_drop_tree(element_body, "li.button-social")
        self.try_drop_tree(element_body, "div.sharecount")
        self.try_drop_tree(element_body, "p.ruledtop")
        self.try_drop_tree(element_body, "p.ctafeedback")
        self.try_drop_tree(element_body, "aside.articlerelated")
        self.try_drop_tree(element_body, "div.sharecount")
        self.try_drop_tree(element_body, "iframe")
        self.clean_relativ_urls(element_body, "http://presseurop.eu")
        return CleanHTML('.')(element_body)

    def get_title(self):
        title = super(self.__class__, self).get_title()
        title = title.split('|')[0]
        return title

    def get_author(self):
        author = super(self.__class__, self).get_author()
        try:
            source = self.doc.getroot().xpath(
                    "//span[@class='sourceinfo']/a")[0]
            source = source.text
            author = author + " | " + source
            return author
        except:
            return author

    def get_daily_date(self):
        plink = self.doc.getroot().xpath("//p[@class='w200']")
        if len(plink) > 0:
            link = plink[0].xpath('a')[0]
            date = link.attrib['href'].split('/')[3]
            return date
        return None
