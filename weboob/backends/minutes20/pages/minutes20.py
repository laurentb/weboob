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
from weboob.tools.parsers.lxmlparser import select 

__all__ = ['Minutes20Page', 'Article']


class Article(object):
    def __init__(self):
        self.title = u''
        self.body = u''
        self.author = None 
        self.date = None

class Minutes20Page(BasePage):
    main_div = NotImplementedError
    element_body = NotImplementedError
    article = Article()
    def set_author(self):
        self.article.author = self.get_element_author().text_content().strip()

    def get_element_author(self):
        return select(self.main_div, "div.mna-signature", 1) 

    def set_body(self):
        self.article.body = self.browser.parser.tostring(select(self.main_div, "div.mna-body", 1))


    def on_loaded(self):
        self.article = Article()
        self.main_div = self.document.getroot()
        self.article.title = select(self.main_div, "h1", 1).text_content()
        self.set_author()
        self.set_body()

    
