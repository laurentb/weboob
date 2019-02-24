# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon
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

import lxml.html

from weboob.browser.filters.standard import CleanText

from .index import DLFPPage


class WikiEditPage(DLFPPage):
    def get_body(self):
        return CleanText('//textarea[has-class("wiki_page_wiki_body")]', default='')(self)

    form_xpath = '//form[@class="new_wiki_page" or @class="edit_wiki_page"]'

    def post_content(self, title, body, message):
        form = self.get_form(xpath=self.form_xpath)

        if title is not None:
            form['wiki_page[title]'] = title.encode('utf-8')
            form['commit'] = 'Créer'
        else:
            form['commit'] = 'Mettre à jour'
        form['wiki_page[wiki_body]'] = body.encode('utf-8')
        if message is not None:
            form['wiki_page[message]'] = message.encode('utf-8')

        form.submit()

    def post_preview(self, body):
        form = self.get_form(xpath=self.form_xpath)
        form['wiki_page[wiki_body]'] = body
        form.submit()

    def get_preview_html(self):
        body = self.doc.xpath('//article[has-class("wikipage")]//div[has-class("content")]')[0]
        return lxml.html.tostring(body)
