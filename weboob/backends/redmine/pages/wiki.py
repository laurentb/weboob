# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
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

class WikiEditPage(BasePage):
    def get_source(self):
        return select(self.document.getroot(), 'textarea#content_text', 1).text

    def set_source(self, data, message):
        self.browser.select_form(nr=1)
        self.browser['content[text]'] = data.encode('utf-8')
        if message:
            self.browser['content[comments]'] = message.encode('utf-8')
        self.browser.submit()

    def get_authenticity_token(self):
        wiki_form = select(self.document.getroot(), 'form#wiki_form', 1)
        return wiki_form.xpath('div/input')[0].get('value')



class WikiPage(BasePage):
    pass
