# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Nicolas Duhamel
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


from weboob.capabilities.bank import Account, AccountNotFound

from weboob.tools.browser import BasePage


__all__ = ['AccountList']


class AccountList(BasePage):
    def on_loaded(self):
        self.account_list = []
        self.parse_table('comptes')
        self.parse_table('comptesEpargne')

    def get_accounts_list(self):
        return self.account_list

    def parse_table(self, what):
        tables = self.document.xpath("//table[@id='%s']" % what, smart_strings=False)
        if len(tables) < 1:
            return

        lines = tables[0].xpath(".//tbody/tr")

        for line  in lines:
            account = Account()
            tmp = line.xpath("./td//a")[0]
            account.label = tmp.text
            account.link_id = tmp.get("href")
            tmp = line.xpath("./td//strong")
            account.id = tmp[0].text
            account.balance = float(''.join(tmp[1].text.replace('.','').replace(',','.').split()))
            self.account_list.append(account)

    def get_account(self, id):
        for account in self.account_list:
            if account.id == id:
                return account
        raise AccountNotFound('Unable to find account: %s' % id)
