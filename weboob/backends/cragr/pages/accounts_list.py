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
from .base import CragrBasePage

class AccountsList(CragrBasePage):
    def on_loaded(self):
        pass

    def get_list(self):
        l = []

        for div in self.document.getiterator('div'):
            if div.attrib.get('class', '') == 'dv' and div.getchildren()[0].tag in ('a', 'br'):
                account = Account()
                if div.getchildren()[0].tag == 'a':
                    # This is at least present on CA Nord-Est
                    account.label = ' '.join(div.find('a').text.split()[:-1])
                    account.id = div.find('a').text.split()[-1]
                    s = div.find('div').find('b').find('span').text
                else:
                    # This is at least present on CA Toulouse
                    account.label = div.find('a').text.strip()
                    account.id = div.findall('br')[1].tail.strip()
                    s = div.find('div').find('span').find('b').text
                balance = u''
                for c in s:
                    if c.isdigit():
                        balance += c
                    if c == ',':
                        balance += '.'
                account.balance = float(balance)
                l.append(account)
        return l
