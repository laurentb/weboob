# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Romain Bignon

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

from weboob.capabilities.bank import Account
from .base import CragrBasePage

class AccountsList(CragrBasePage):
    def loaded(self):
        pass

    def get_list(self):
        l = []
        for div in self.document.getiterator('div'):
            if div.attrib.get('class', '') == 'dv' and div.getchildren()[0].tag == 'a':
                a = div.getchildren()[0]
                account = Account()
                account.setLabel(a.text.strip())
                account.setID(long(a.getchildren('br')[0].tail.strip()))
                balance = a.getchildren('span')[0].getchildren('span')[0].getchildren('b')[0].text
                balance = balance.replace(',', '.').replace(u' ', '').replace(u' €', '')
                account.setBalance(float(balance))
        return l
