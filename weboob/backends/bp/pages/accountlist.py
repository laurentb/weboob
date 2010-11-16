# -*- coding: utf-8 -*-

# Copyright(C) 2010  Nicolas Duhamel
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
        self.Account_List = []

    def get_accounts_list(self):

        #Parse CCP
        compte_table = self.document.xpath("//table[@id='comptes']", smart_strings=False)[0]
        compte_ligne = compte_table.xpath("./tbody/tr")

        for compte in compte_ligne:
            account = Account()
            tp = compte.xpath("./td/a")[0]
            account.label = tp.text
            account.link_id = tp.get("href")
            account.id = compte.xpath("./td")[1].text
            account.balance = float(''.join( compte.xpath("./td/span")[0].text.replace('.','').replace(',','.').split() ))
            self.Account_List.append(account)

        #Parse epargne
        epargne_table = self.document.xpath("//table[@id='comptesEpargne']", smart_strings=False)[0]
        epargne_ligne = epargne_table.xpath("./tbody/tr")

        for epargne in epargne_ligne:
            account = Account()
            tp = epargne.xpath("./td/a")[0]
            account.label = tp.text
            account.link_id = tp.get("href")
            account.id = epargne.xpath("./td")[1].text
            account.balance = float(''.join( epargne.xpath("./td/span")[0].text.replace('.','').replace(',','.').split() ) )
            self.Account_List.append(account)

        return self.Account_List

    def get_account(self, id):
        if not self.Account_List:
            self.get_accounts_list()

        for account in self.Account_List:
                if account.id == id:
                    return account
        raise AccountNotFound('Unable to find account: %s' % id)
