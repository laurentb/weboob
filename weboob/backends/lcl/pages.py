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


from weboob.capabilities.bank import Account
from weboob.tools.browser import BasePage

class LoginPage(BasePage):
    def login(self, agency, login, passwd):
        self.browser.select_form(nr=0)
        self.browser['agenceId'] = agency
        self.browser['compteId'] = login
        self.browser['CodeId'] = passwd
        self.browser.submit()

class LoginErrorPage(BasePage):
    pass

class FramePage(BasePage):
    pass


class AccountsPage(BasePage):
    def get_list(self):
      l = []
      for div in self.document.getiterator('div'):
        if div.attrib.get('class')=="unCompte-CC" :
          account = Account()
          account.id = div.attrib.get('id').replace('-','')
          for td in div.getiterator('td'):
            if td.find("div") is not None and td.find("div").attrib.get('class') == 'libelleCompte':
              account.label = td.find("div").text
            elif td.find('a') is not None and td.find('a').attrib.get('class') is None:
              balance = td.find('a').text.replace(u"\u00A0",'').replace('.','').replace('+','').replace(',','.')
              account.balance = float(balance)
              account.link_id = td.find('a').attrib.get('href')

          l.append(account)

      return l
