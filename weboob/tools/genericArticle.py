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

def try_remove(base_element, selector):
    try :
        base_element.remove(select(base_element, selector, 1 ))
    except (SelectElementException, ValueError):
        pass


class NoAuthorElement(SelectElementException):
    pass

class NoneMainDiv(AttributeError):
    pass

class Article(object):
    author = u''

    def __init__(self, browser, _id):
        self.browser = browser
        self.id = _id
        self.title = u''
        self.body = u''
        self.url = u''
        self.date = None

class GenericNewsPage(BasePage):
    __element_body = NotImplementedError
    __article = Article
    element_title_selector  = NotImplementedError 
    main_div = NotImplementedError
    element_body_selector = NotImplementedError
    element_author_selector = NotImplementedError

    def get_body(self):
        return self.browser.parser.tostring(self.get_element_body())

    def get_author(self):
        try:
            return self.get_element_author().text_content().strip()
        except NoAuthorElement:
            return self.__article.author

    def get_title(self):
        return select(
            self.main_div,
            self.element_title_selector,
            1).text_content().strip()

    def get_element_body(self):
        return select(self.main_div, self.element_body_selector, 1)

    def get_element_author(self):
        try:
            return select(self.main_div, self.element_author_selector, 1)
        except SelectElementException:
            raise NoAuthorElement()
        except AttributeError:
            if self.main_div == None:
                raise NoneMainDiv("main_div is none on %s" % (self.browser))
            else:
                raise

    def get_article(self, _id):
        __article = Article(self.browser, _id)
        __article.author = self.get_author()
        __article.title  = self.get_title()
        __article.url    = self.url
        __article.body   = self.get_body()

        return __article
