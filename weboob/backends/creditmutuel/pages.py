# -*- coding: utf-8 -*-

# Copyright(C) 2010  Julien Veyssier
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
from weboob.capabilities.bank import Account

class LoginPage(BasePage):
    def login(self, login, passwd):
        self.browser.select_form(nr=0)
        self.browser['_cm_user'] = login
        self.browser['_cm_pwd'] = passwd
        self.browser.submit()

class LoginErrorPage(BasePage):
    pass

class AccountsPage(BasePage):
    def get_list(self):
        l = []
        
        for tr in self.document.getiterator('tr'):
            first_td = tr.getchildren()[0]
            if first_td.attrib.get('class', '') == 'i g' or first_td.attrib.get('class', '') == 'p g':
                account = Account()
                account.label = first_td.find('a').text
                account.link_id = first_td.find('a').get('href', '')
                account.id = first_td.find('a').text.split(' ')[0]+first_td.find('a').text.split(' ')[1]
                s = tr.getchildren()[2].text
                balance = u''
                for c in s:
                    if c.isdigit():
                        balance += c
                    if c == ',':
                        balance += '.'
                account.balance = float(balance)
                l.append(account)
            #raise NotImplementedError()
        return l
