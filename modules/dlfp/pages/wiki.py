# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon
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

from weboob.deprecated.browser import BrokenPageError

from .index import DLFPPage


class WikiEditPage(DLFPPage):
    def get_body(self):
        try:
            return self.parser.select(self.document.getroot(), 'textarea#wiki_page_wiki_body', 1).text
        except BrokenPageError:
            return ''

    def _is_wiki_form(self, form):
        return form.attrs.get('class', '') in ('new_wiki_page', 'edit_wiki_page')

    def post_content(self, title, body, message):
        self.browser.select_form(predicate=self._is_wiki_form)
        self.browser.set_all_readonly(False)

        if title is not None:
            self.browser['wiki_page[title]'] = title.encode('utf-8')
            self.browser['commit'] = 'Créer'
        else:
            self.browser['commit'] = 'Mettre à jour'
        self.browser['wiki_page[wiki_body]'] = body.encode('utf-8')
        if message is not None:
            self.browser['wiki_page[message]'] = message.encode('utf-8')

        self.browser.submit()

    def post_preview(self, body):
        self.browser.select_form(predicate=self._is_wiki_form)
        self.browser['wiki_page[wiki_body]'] = body
        self.browser.submit()

    def get_preview_html(self):
        body = self.parser.select(self.document.getroot(), 'article.wikipage div.content', 1)
        return self.parser.tostring(body)
