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

from weboob.browser.pages import HTMLPage
from weboob.browser.filters.html import XPath, XPathNotFound
from weboob.browser.filters.standard import CleanText
from lxml.etree import Comment


class Article(object):
    author = u''
    title = u''

    def __init__(self, browser, _id):
        self.browser = browser
        self.id = _id
        self.body = u''
        self.url = u''
        self.date = None


class GenericNewsPage(HTMLPage):
    __element_body = NotImplementedError
    __article = Article
    element_title_selector = NotImplementedError
    main_div = NotImplementedError
    element_body_selector = NotImplementedError
    element_author_selector = NotImplementedError
    _selector = XPath

    def on_load(self):
        self.handle_refresh()
        self.on_loaded()

    def on_loaded(self):
        pass

    def get_body(self):
        try:
            return CleanText('.')(self.get_element_body())
        except (AttributeError):
            return self.__article.body

    def get_author(self):
        try:
            return CleanText('.')(self.get_element_author())
        except (AttributeError):
            return self.__article.author

    def get_title(self):
        try:
            return CleanText(self._selector(self.element_title_selector))(self.main_div)
        except AttributeError:
            if self.main_div is None:
                raise XPathNotFound("main_div is none on %s" % (self.browser))
            elif self.element_title_selector != 'h1':
                self.element_title_selector = 'h1'
                return self.get_title()
            else:
                raise AttributeError("no title on %s" % (self.browser))

    def get_element_body(self):
        try:
            return self._selector(self.element_body_selector)(self.main_div)[0]
        except (AttributeError, IndexError):
            if self.main_div is None:
                raise XPathNotFound("main_div is none on %s" % (self.browser))
            else:
                raise AttributeError("no body on %s" % (self.browser))

    def get_element_author(self):
        try:
            return self._selector(self.element_author_selector)(self.main_div)[0]
        except IndexError:
            if self.main_div is None:
                raise XPathNotFound("main_div is none on %s" % (self.browser))
            else:
                raise AttributeError("no author on %s" % (self.browser))

    def get_article(self, _id):
        __article = Article(self.browser, _id)
        __article.author = self.get_author()
        __article.title  = self.get_title()
        __article.url    = self.url
        __article.body   = self.get_body()

        return __article

    def drop_comments(self, base_element):
        for comment in base_element.getiterator(Comment):
            comment.drop_tree()

    def try_remove(self, base_element, selector):
        for el in self._selector(selector)(base_element):
            try:
                el.getparent().remove(el)
            except (AttributeError, ValueError):
                continue

    def remove_from_selector_list(self, base_element, selector_list):
        for selector in selector_list:
            base_element.remove(self._selector(selector)(base_element))

    def try_remove_from_selector_list(self, base_element, selector_list):
        for selector in selector_list:
            self.try_remove(base_element, selector)

    def try_drop_tree(self, base_element, selector):
        for el in self._selector(selector)(base_element):
            el.drop_tree()

    @staticmethod
    def clean_relativ_urls(base_element, domain):
        for a in base_element.findall('.//a'):
            if "href" in a.attrib:
                if a.attrib["href"] and a.attrib["href"][0:7] != "http://" and a.attrib["href"][0:7] != "https://":
                    a.attrib["href"] = domain + a.attrib["href"]
        for img in base_element.findall('.//img'):
            if img.attrib["src"][0:7] != "http://" and img.attrib["src"][0:7] != "https://":
                img.attrib["src"] = domain + img.attrib["src"]
