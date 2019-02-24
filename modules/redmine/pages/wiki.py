# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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

from .index import BaseHTMLPage


class WikiEditPage(BaseHTMLPage):
    def get_source(self):
        return self.doc.xpath('//textarea[@id="content_text"]')[0].text

    def set_source(self, data, message):
        form = self.get_form(nr=1)
        form['content[text]'] = data
        if message:
            form['content[comments]'] = message
        form.submit()

    def get_authenticity_token(self):
        form = self.get_form(id='wiki_form')
        return form['authenticity_token']

    def get_submit(self):
        return self.get_form(id='wiki_form')


class WikiPage(BaseHTMLPage):
    pass
