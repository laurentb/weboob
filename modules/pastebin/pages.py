# -*- coding: utf-8 -*-

# Copyright(C) 2011-2012 Laurent Bachelier
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


from weboob.tools.browser import BasePage, BrokenPageError

__all__ = ['PastePage', 'PostPage', 'LoginPage']


class BasePastebinPage(BasePage):
    def is_logged(self):
        header = self.parser.select(self.document.getroot(),
                'id("header_bottom")/ul[@class="top_menu"]', 1, 'xpath')
        for link in header.xpath('//ul/li/a'):
            if link.text == 'logout':
                return True
            if link.text == 'login':
                return False


class LoginPage(BasePastebinPage):
    def login(self, username, password):
        self.browser.select_form(nr=1)
        self.browser['user_name'] = username.encode(self.browser.ENCODING)
        self.browser['user_password'] = password.encode(self.browser.ENCODING)
        self.browser.submit()


class PastePage(BasePastebinPage):
    def fill_paste(self, paste):
        header = self.parser.select(self.document.getroot(),
                'id("content_left")//div[@class="paste_box_info"]', 1, 'xpath')
        paste.title = unicode(self.parser.select(header,
                '//div[@class="paste_box_line1"]//h1', 1, 'xpath').text)
        paste.contents = unicode(self.parser.select(self.document.getroot(),
                '//textarea[@id="paste_code"]', 1, 'xpath').text)
        visibility_text = self.parser.select(header,
                '//div[@class="paste_box_line1"]//img', 1, 'xpath').attrib['title']
        if visibility_text.startswith('Public'):
            paste.public = True
        elif visibility_text.startswith('Unlisted') or visibility_text.startswith('Private'):
            paste.public = False
        else:
            raise BrokenPageError('Unable to get the paste visibility')
        return paste

    def get_id(self):
        """
        Find out the ID from the URL
        """
        return self.group_dict['id']


class PostPage(BasePastebinPage):
    def post(self, paste, expiration=None):
        self.browser.select_form(name='myform')
        self.browser['paste_code'] = paste.contents.encode(self.browser.ENCODING)
        self.browser['paste_name'] = paste.title.encode(self.browser.ENCODING)
        if paste.public is True:
            self.browser['paste_private'] = ['0']
        elif paste.public is False:
            self.browser['paste_private'] = ['1']
        if expiration:
            self.browser['paste_expire_date'] = [expiration]
        self.browser.submit()


class UserPage(BasePastebinPage):
    pass
