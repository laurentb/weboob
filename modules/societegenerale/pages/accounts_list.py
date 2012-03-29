# -*- coding: utf-8 -*-

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


from decimal import Decimal
import re

from weboob.capabilities.bank import Account
from weboob.tools.browser import BasePage

class AccountsList(BasePage):
    LINKID_REGEXP = re.compile(".*ch4=(\w+).*")

    def on_loaded(self):
        pass

    def get_list(self):
        l = []
        for tr in self.document.getiterator('tr'):
            if 'LGNTableRow' in tr.attrib.get('class', '').split():
                account = Account()
                for td in tr.getiterator('td'):
                    if td.attrib.get('headers', '') == 'TypeCompte':
                        a = td.find('a')
                        account.label = a.find("span").text
                        account._link_id = a.get('href', '')

                    elif td.attrib.get('headers', '') == 'NumeroCompte':
                        id = td.text
                        id = id.replace(u'\xa0','')
                        account.id = id

                    elif td.attrib.get('headers', '') == 'Libelle':
                        pass

                    elif td.attrib.get('headers', '') == 'Solde':
                        balance = td.find('div').text
                        if balance != None:
                            balance = balance.replace(u'\xa0','').replace(',','.')
                            account.balance = Decimal(balance)
                        else:
                            account.balance = Decimal(0.0)

                l.append(account)

        return l
