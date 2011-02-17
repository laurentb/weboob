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

class NoAuthorElement(Exception):
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
    main_div = NotImplementedError
    element_body = NotImplementedError
    article = Article
    element_author_selector = ValueError
    element_title_selector  = ValueError
    element_body_selector   = ValueError

    def get_body(self):
        return self.browser.parser.tostring(self.element_body)

    def get_author(self):
        return select(self.main_div, self.element_author_selector, 1).text_content().strip()

    def get_title(self):
       return select(self.main_div, self.element_title_selector, 1).text_content().strip()

    def on_loaded(self):
        self.article = Article(self.browser, url2id(self.url) )
        self.main_div = self.document.getroot()

        self.element_author_selector    = "div.mna-signature"
        self.element_title_selector     = "h1"
        self.element_body_selector      = "div.mna-body"

        self.element_body = select(self.main_div, self.element_body_selector, 1)

        self.article.author = self.get_author()
        self.article.title  = self.get_title()
        self.article.url    = self.url
        self.article.body   = self.get_body()

