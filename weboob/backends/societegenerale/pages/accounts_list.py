# -*- coding: utf-8 -*-

# Copyright(C) 2010  Jocelyn Jaubert
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


import re

from weboob.capabilities.bank import Account
from weboob.capabilities.base import NotAvailable
from weboob.tools.browser import BasePage
from lxml import etree

class AccountsList(BasePage):
    LINKID_REGEXP = re.compile(".*ch4=(\w+).*")

    def on_loaded(self):
        pass

    def get_list(self):
        l = []
        for tr in self.document.getiterator('tr'):
            if tr.attrib.get('class', '') == 'LGNTableRow':
                account = Account()
                for td in tr.getiterator('td'):
                    if td.attrib.get('headers', '') == 'TypeCompte':
                        a = td.find('a')
                        account.label = a.text
                        account.link_id = a.get('href', '')

                    elif td.attrib.get('headers', '') == 'NumeroCompte':
                        id = td.text
                        id = id.replace(u'\xa0','')
                        account.id = id

                    elif td.attrib.get('headers', '') == 'Libelle':
                        pass

                    elif td.attrib.get('headers', '') == 'Solde':
                        balance = td.text
                        balance = balance.replace(u'\xa0','').replace(',','.')
                        if balance != "":
                            account.balance = float(balance)
                        else:
                            account.balance = 0.0

                l.append(account)

        return l
