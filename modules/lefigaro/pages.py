"ArticlePage object for lefigaro"
# -*- coding: utf-8 -*-

# Copyright(C) 2011  Julien Hebert
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.
from weboob.browser.pages import AbstractPage
from weboob.browser.filters.html import CSS
from weboob.browser.filters.standard import CleanText


class ArticlePage(AbstractPage):
    "ArticlePage object for lefigaro"
    _selector = CSS
    PARENT = 'genericnewspaper'
    PARENT_URL = 'generic_news_page'

    def on_loaded(self):
        self.main_div = self.doc.getroot()
        self.element_title_selector = "h1"
        self.element_author_selector = 'span[itemprop="author"], span.auteur_long>div'
        self.element_body_selector = "article div[itemprop='articleBody']"

    def get_body(self):
        element_body = self.get_element_body()
        self.drop_comments(element_body)
        self.try_drop_tree(element_body, "script")
        self.try_drop_tree(element_body, "liste")

        self.try_remove_from_selector_list(element_body, ["div#article-comments", "div.infos", "div.photo",
                                                          "div.art_bandeau_bottom", "div.view",
                                                          "span.auteur_long", "#toolsbar", 'link', 'figure'])

        for image in self._selector('img')(element_body):
            if image.attrib['src'].endswith('coeur-.gif'):
                image.drop_tree()

        for div in self._selector('div')(element_body):
            if div.text == ' Player Figaro BFM ':
                obj = div.getnext()
                a = obj.getnext()
                if obj.tag == 'object':
                    obj.drop_tree()
                if a.tag == 'a' and 'BFM' in a.text:
                    a.drop_tree()
                div.drop_tree()

        # This part of the article seems manually generated.
        check_next = False
        for crappy_content in self._selector('b, a')(element_body):
            if check_next is True:
                # Remove if it has only links
                if crappy_content.tag == 'a':
                    element_body.remove(crappy_content)
                check_next = False

            if crappy_content.text == 'LIRE AUSSI :' or crappy_content.text == 'LIRE AUSSI:':
                element_body.remove(crappy_content)
                check_next = True

        txts = element_body.find_class("texte")
        if len(txts) > 0:
            txts[0].drop_tag()
        element_body.tag = "div"
        return CleanText('.')(element_body)
