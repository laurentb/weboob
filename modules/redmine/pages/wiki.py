# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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


from weboob.deprecated.browser import Page


class WikiEditPage(Page):
    def get_source(self):
        return self.parser.select(self.document.getroot(), 'textarea#content_text', 1).text

    def set_source(self, data, message):
        self.browser.select_form(nr=1)
        self.browser['content[text]'] = data.encode('utf-8')
        if message:
            self.browser['content[comments]'] = message.encode('utf-8')
        self.browser.submit()

    def get_authenticity_token(self):
        wiki_form = self.parser.select(self.document.getroot(), 'form#wiki_form', 1)
        return wiki_form.xpath('div/input')[0].get('value')


class WikiPage(Page):
    pass
