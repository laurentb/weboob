"ArticlePage object for lefigaro"
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

from weboob.tools.capabilities.messages.genericArticle import GenericNewsPage, drop_comments, try_drop_tree, try_remove_from_selector_list


class ArticlePage(GenericNewsPage):
    "ArticlePage object for lefigaro"
    def on_loaded(self):
        self.main_div = self.document.getroot()
        self.element_title_selector = "h1"
        self.element_author_selector    = "span.auteur>a, span.auteur_long>div"
        self.element_body_selector      = "article div.fig-article-body"

    def get_body(self):
        element_body = self.get_element_body()
        drop_comments(element_body)
        try_drop_tree(self.parser, element_body, "script")
        try_drop_tree(self.parser, element_body, "liste")

        try_remove_from_selector_list(self.parser, element_body, ["div#article-comments", "div.infos", "div.photo", "div.art_bandeau_bottom", "div.view", "span.auteur_long", "#toolsbar", 'link'])

        for image in self.parser.select(element_body, 'img'):
            if image.attrib['src'].endswith('coeur-.gif'):
                image.drop_tree()

        for div in self.parser.select(element_body, 'div'):
            if div.text == ' Player Figaro BFM ':
                obj = div.getnext()
                a = obj.getnext()
                if obj.tag == 'object':
                    obj.drop_tree()
                if a.tag == 'a' and 'BFM' in a.text:
                    a.drop_tree()
                div.drop_tree()

        # This part of the article seems manually generated.
        for crappy_title in self.parser.select(element_body, 'p strong'):
            if crappy_title.text == 'LIRE AUSSI :' or crappy_title.text == 'LIRE AUSSI:':
                # Remove if it has only links
                for related in crappy_title.getparent().itersiblings(tag='p'):
                    if len(related) == len(list(related.iterchildren(tag='a'))):
                        related.drop_tree()
                    else:
                        break
                crappy_title.drop_tree()

        txts = element_body.find_class("texte")
        if len(txts) > 0:
            txts[0].drop_tag()
        element_body.tag = "div"
        return self.parser.tostring(element_body)


class ActuPage(GenericNewsPage):
    def on_loaded(self):
        self.main_div = self.document.getroot()
        self.element_title_selector     = "h2"
        self.element_author_selector    = "div.name>span"
        self.element_body_selector      = ".block-text"

    def get_body(self):
        element_body = self.get_element_body()
        try_remove_from_selector_list(self.parser, element_body, ['div'])
        element_body.tag = "div"
        return self.parser.tostring(element_body)
