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
from weboob.tools.browser import BasePage
from weboob.tools.parsers.lxmlparser import select, SelectElementException
from weboob.backends.minutes20.tools import url2id
__all__ = ['Minutes20Page', 'Article', 'NoAuthorElement']

class NoAuthorElement(SelectElementException):
    pass

class Article(object):
    def __init__(self, browser, _id):
        self.browser = browser
        self.id = _id
        self.title = u''
        self.body = u''
        self.url = u''
        self.author = u''
        self.date = None

class Minutes20Page(BasePage):
    __main_div = NotImplementedError
    __element_body = NotImplementedError
    __article = Article
    __element_author_selector = ValueError
    __element_title_selector  = ValueError
    __element_body_selector   = ValueError

    def get_body(self):
        return self.browser.parser.tostring(self.get_element_body())

    def get_author(self):
        try:
            return self.get_element_author().text_content().strip()
        except NoAuthorElement:
            return None

    def get_title(self):
       return select(self.__main_div, self.__element_title_selector, 1).text_content().strip()

    def get_element_body(self):
        return select(self.__main_div, self.__element_body_selector, 1)

    def get_element_author(self):
        try:
            return select(self.__main_div, self.__element_author_selector, 1)
        except SelectElementException:
            raise NoAuthorElement()

    def get_article(self):
        __article = Article(self.browser, url2id(self.url) )
        __article.author = self.get_author()
        __article.title  = self.get_title()
        __article.url    = self.url
        __article.body   = self.get_body()

        return __article

    def on_loaded(self):
        self.__main_div = self.document.getroot()

        self.__element_author_selector    = "div.mna-signature"
        self.__element_title_selector     = "h1"
        self.__element_body_selector      = "div.mna-body"

