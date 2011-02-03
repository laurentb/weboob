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

class Article(object):
    def __init__(self):
        self.title = u''
        self.body = u''
        self.author =None 
        self.date = None

class ArticlePage(BasePage):
    def on_loaded(self):
        self.article = Article()
        main_div = self.document.getroot()
        self.article.title = select(main_div, "h1", 1).text_content()
        element_body = select(main_div, "div.mn-line>div.mna-body", 1) 
        element_tools = select(element_body, "div.mna-tools", 1)
        element_comment  = select(element_body, "div.mna-comment-call", 1)
        element_author = select(element_body, "#mna-signature", 1)
        element_body.remove(element_tools)
        element_body.remove(element_comment)
        element_body.remove(element_author)
        self.article.author = element_author.text_content().strip()
        self.article.body = self.browser.parser.tostring(element_body)

    def get_content(self):
        return self.article
