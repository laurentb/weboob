# -*- coding: utf-8 -*-

# Copyright(C) 2012 Roger Philibert
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

class LoginPage(BasePage):
    def login(self, username, password):
        self.browser.select_form(name='loginf')
        self.browser['username'] = username.encode(self.browser.ENCODING)
        self.browser['password'] = password.encode(self.browser.ENCODING)
        self.browser.submit(id='login_btn', nologin=True)

class ThreadPage(BasePage):
    def get_threads(self):
        li_elems = self.parser.select(self.document.getroot(), "//div[@id='page_content']//li", method= 'xpath')

        threads = []
        for elem in li_elems:
            _class = elem.get('class', '')
            if 'clearfix' in _class.split():
                threads.append({
                        u'username' : elem.getchildren()[0].get('href').split('/')[-1],
                        u'id' : elem.get('id', '').split('_')[1],
                })

        return threads

class MessagesPage(BasePage):
    def get_thread_mails(self, count):
        ul_item = self.parser.select(self.document.getroot(), "//ul[@id='rows']", method='xpath')[0]

        mails = {
            'member' : {},
            'messages' : [],
        }

        for li_msg in ul_item.getchildren():
            div = li_msg.getchildren()[1]
            txt = self.parser.tostring(div.getchildren()[1])
            date = div.getchildren()[2].text
            id_from = li_msg.getchildren()[0].get('href').split('/')[-1]

            mails['messages'].append({
                'date' : date,
                'message' : txt,
                'id_from' : id_from,
            })

        return mails
