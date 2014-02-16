# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Nicolas Duhamel
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

from weboob.capabilities.bank import Account, AccountNotFound
from weboob.tools.browser import BasePage
from weboob.tools.misc import to_unicode
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.ordereddict import OrderedDict


__all__ = ['AccountList']


class AccountList(BasePage):
    def on_loaded(self):
        self.accounts = OrderedDict()
        self.parse_table('comptes',         Account.TYPE_CHECKING)
        self.parse_table('comptesEpargne',  Account.TYPE_SAVINGS)
        self.parse_table('comptesTitres',   Account.TYPE_MARKET)
        self.parse_table('comptesVie',      Account.TYPE_DEPOSIT)
        self.parse_table('comptesRetraireEuros')

    def get_accounts_list(self):
        return self.accounts.itervalues()

    def parse_table(self, what, actype=Account.TYPE_UNKNOWN):
        tables = self.document.xpath("//table[@id='%s']" % what, smart_strings=False)
        if len(tables) < 1:
            return

        lines = tables[0].xpath(".//tbody/tr")
        for line in lines:
            account = Account()
            tmp = line.xpath("./td//a")[0]
            account.label = to_unicode(tmp.text)
            account.type = actype
            account._link_id = tmp.get("href")
            if 'BourseEnLigne' in account._link_id:
                account.type = Account.TYPE_MARKET

            tmp = line.xpath("./td/span/strong")
            if len(tmp) >= 2:
                tmp_id = tmp[0].text
                tmp_balance = tmp[1].text
            else:
                tmp_id = line.xpath("./td//span")[1].text
                tmp_balance = tmp[0].text

            account.id = tmp_id
            account.currency = account.get_currency(tmp_balance)
            account.balance = Decimal(FrenchTransaction.clean_amount(tmp_balance))

            if account.id in self.accounts:
                a = self.accounts[account.id]
                a._card_links.append(account._link_id)
                if not a.coming:
                    a.coming = Decimal('0.0')
                a.coming += account.balance
            else:
                account._card_links = []
                self.accounts[account.id] = account

    def get_account(self, id):
        try:
            return self.accounts[id]
        except KeyError:
            raise AccountNotFound('Unable to find account: %s' % id)
