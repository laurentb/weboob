# -*- coding: utf-8 -*-

# Copyright(C) 2011 Laurent Bachelier
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


from weboob.tools.browser import BasePage

__all__ = ['PastePage', 'PostPage']

class PastePage(BasePage):
    def fill_paste(self, paste):
        header = self.parser.select(self.document.getroot(),
                'id("content_left")//div[@class="paste_box_info"]', 1, 'xpath')
        paste.title = self.parser.select(header,
                '//div[@class="paste_box_line1"]//h1', 1, 'xpath').text
        paste.contents = self.parser.select(self.document.getroot(),
                '//textarea[@id="paste_code"]', 1, 'xpath').text
        return paste

    def get_id(self):
        """
        Find out the ID from the URL
        """
        return self.group_dict['id']


class PostPage(BasePage):
    def post(self, paste):
        self.browser.select_form(name='myform')
        self.browser['paste_code'] = paste.contents.encode(self.browser.ENCODING)
        self.browser['paste_name'] = paste.title.encode(self.browser.ENCODING)
        self.browser['paste_expire_date'] = ['1M']
        self.browser.submit()
