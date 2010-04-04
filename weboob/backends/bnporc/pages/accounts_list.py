# -*- coding: utf-8 -*-

"""
Copyright(C) 2009-2010  Romain Bignon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

import re

from weboob.capabilities.bank import Account
from weboob.tools.browser import BasePage
from weboob.tools.parser import tostring

class AccountsList(BasePage):
    LINKID_REGEXP = re.compile(".*ch4=(\w+).*")

    def loaded(self):
        pass

    def get_list(self):
        l = []
        for tr in self.document.getiterator('tr'):
            if tr.attrib.get('class', '') == 'comptes':
                account = Account()
                for td in tr.getiterator('td'):
                    if td.attrib.get('headers', '').startswith('Numero_'):
                        id = td.text
                        account.setID(long(''.join(id.split(' '))))
                    elif td.attrib.get('headers', '').startswith('Libelle_'):
                        a = td.findall('a')
                        label = unicode(a[0].text)
                        account.setLabel(label)
                        m = self.LINKID_REGEXP.match(a[0].attrib.get('href', ''))
                        if m:
                            account.setLinkID(m.group(1))
                    elif td.attrib.get('headers', '').startswith('Solde'):
                        a = td.findall('a')
                        balance = a[0].text
                        balance = balance.replace('.','').replace(',','.')
                        account.setBalance(float(balance))
                    elif td.attrib.get('headers', '').startswith('Avenir'):
                        a = td.findall('a')
                        coming = a[0].text
                        coming = coming.replace('.','').replace(',','.')
                        account.setComing(float(coming))

                l.append(account)
        return l
