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

class ArticlePage(BasePage):
    def get_title(self):
        return select(self.document.getroot(), "h1", 1).text_content()

    def get_article(self):
        main_div = self.document.getroot()
        article_body = select(main_div, "div.mn-line>div.mna-body")[0] 
        txt_article = article_body.text_content()
        txt_to_remove = select(article_body, "div.mna-tools")[0].text_content()
        txt_to_remove2 = select(main_div, "div.mn-line>div.mna-body>div.mna-comment-call")[0].text_content()
        return txt_article.replace(txt_to_remove, '', 1).replace( txt_to_remove2, '', 1)

    def get_content(self):
        title = self.get_title()
        content = self.get_article()
        return [title, content] 
