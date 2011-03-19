# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon
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

from weboob.tools.parsers.lxmlparser import select, SelectElementException

from .index import DLFPPage

class WikiEditPage(DLFPPage):
    def get_body(self):
        try:
            return select(self.document.getroot(), 'textarea#wiki_page_wiki_body', 1).text
        except SelectElementException:
            return ''

    def _is_wiki_form(self, form):
        return form.attrs.get('class', '') in ('new_wiki_page', 'edit_wiki_page')

    def post_content(self, title, body, message):
        self.browser.select_form(predicate=self._is_wiki_form)
        self.browser.set_all_readonly(False)

        if title is not None:
            self.browser['wiki_page[title]'] = title
            self.browser['commit'] = 'Créer'
        else:
            self.browser['commit'] = 'Mettre à jour'
        self.browser['wiki_page[wiki_body]'] = body
        if message is not None:
            self.browser['wiki_page[message]'] = message

        self.browser.submit()

    def post_preview(self, body):
        self.browser.select_form(predicate=self._is_wiki_form)
        self.browser['wiki_page[wiki_body]'] = body
        self.browser.submit()

    def get_preview_html(self):
        body = select(self.document.getroot(), 'article.wikipage div.content', 1)
        return self.browser.parser.tostring(body)
