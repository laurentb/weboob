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

from weboob.browser.pages import AbstractPage
from weboob.browser.filters.html import CSS, CleanHTML


class ArticlePage(AbstractPage):
    "ArticlePage object for taz"
    _selector = CSS
    PARENT = 'genericnewspaper'
    PARENT_URL = 'generic_news_page'

    def on_loaded(self):
        self.main_div = self.doc.getroot()
        self.element_title_selector = "title"
        self.element_author_selector = 'a[rel="author"]>h4'

    def get_body(self):
        div = self.doc.getroot().find('.//div[@class="sectbody"]')
        self.try_drop_tree(div, "div.anchor")
        self.try_drop_tree(div, "script")
        self.clean_relativ_urls(div, "http://taz.de")
        return CleanHTML('.')(div)
