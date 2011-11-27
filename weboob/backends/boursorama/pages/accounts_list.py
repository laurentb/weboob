# -*- coding: utf-8 -*-

# Copyright(C) 2011      Gabriel Kerneis
# Copyright(C) 2010-2011 Jocelyn Jaubert
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


import re

from weboob.capabilities.bank import Account
from weboob.tools.browser import BasePage

class AccountsList(BasePage):

    def on_loaded(self):
        pass

    def get_list(self):
        l = []
        for div in self.document.getiterator('div'):
            if div.attrib.get('id', '') == 'synthese-list':
                for tr in div.getiterator('tr'):
                    account = Account()
                    for td in tr.getiterator('td'):
                       if td.attrib.get('class', '') == 'account-cb':
                           break
        
                       elif td.attrib.get('class', '') == 'account-name':
                           a = td.find('a')
                           account.label = a.text
                           account.link_id = a.get('href', '')
        
                       elif td.attrib.get('class', '') == 'account-number':
                           id = td.text
                           id = id.strip(u' \n\t')
                           account.id = id
        
                       elif td.attrib.get('class', '') == 'account-total':
                           span = td.find('span')
                           if span == None:
                               balance = td.text
                           else:
                               balance = span.text
                           balance = balance.strip(u' \n\t€+').replace(',','.').replace(' ','')
                           if balance != "":
                               account.balance = float(balance)
                           else:
                               account.balance = 0.0
        
                    else:
                           # because of some weird useless <tr>
                           if account.id != 0:
                               l.append(account)

        return l
