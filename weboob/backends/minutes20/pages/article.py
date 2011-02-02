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

class Article(object):
    def __init__(self):
        self.title = u''
        self.body = u''
        self.author =None 
        self.date = None

class ArticlePage(BasePage):
    def on_loaded(self):
        self.article = None
        self.set_article()

    def set_article(self):
        self.article = Article()
        #elp(self.get_title().encode('iso8859-1'))
        self.article.title = self.get_title()
        self.article.body = self.get_article()


    def get_title(self):
        return self.browser.parser.tostring(select(self.document.getroot(), "h1", 1))

    def get_article(self):
        main_div = self.document.getroot()
        article_body = select(main_div, "div.mn-line>div.mna-body")[0] 
        txt_article = article_body.text_content()
        txt_to_remove = select(article_body, "div.mna-tools")[0].text_content()
        txt_to_remove2 = select(main_div, "div.mn-line>div.mna-body>div.mna-comment-call")[0].text_content()
        return txt_article.replace(txt_to_remove, '', 1).replace( txt_to_remove2, '', 1)

    def get_content(self):
        return self.article
