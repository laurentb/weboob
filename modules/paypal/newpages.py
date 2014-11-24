# -*- coding: utf-8 -*-

# Copyright(C) 2014 Budget Insight
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

from weboob.deprecated.browser import Page
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.date import parse_french_date


class NewHomePage(Page):
    pass

class NewAccountPage(Page):
    def get_account(self, _id):
        return self.get_accounts().get(_id)

    def get_accounts(self):
        accounts = {}
        content = self.document.xpath('//div[@id="moneyPage"]')[0]

        # Primary currency account
        primary_account = Account()
        primary_account.type = Account.TYPE_CHECKING
        balance = self.parser.tocleanstring(content.xpath('//div[contains(@class, "col-md-6")][contains(@class, "available")]')[0])
        primary_account.currency = Account.get_currency(balance)
        primary_account.id = unicode(primary_account.currency)

        primary_account.balance = Decimal(FrenchTransaction.clean_amount(balance))

        primary_account.label = u'%s %s*' % (self.browser.username, balance.split()[-1])

        accounts[primary_account.id] = primary_account

        return accounts

class NewHistoryPage(Page):

    def iter_transactions(self, account):
        for trans in self.parse():
            if trans._currency == account.currency:
                yield trans

    def parse(self):
        for i, tr in enumerate(self.document.xpath('//tr')):
            t = FrenchTransaction(tr.xpath('./td[@class="transactionId"]/span')[0].text.strip())
            date = parse_french_date(tr.xpath('./td[@class="date"]')[0].text.strip())
            status = tr.xpath('./td[@class="desc"]/ul/li[@class="first"]')[0].text.strip()
            #We pass this because it's not transaction
            if status == u'Créé' or status == u'Annulé':
                continue
            raw = tr.xpath('./td[@class="desc"]/strong')[0].text.strip()
            t.parse(date=date, raw=raw)
            amount = tr.xpath('./td[@class="price"]/span')[0].text.strip()
            t.set_amount(amount)
            t._currency = Account.get_currency(amount)
            yield t

    def transaction_left(self):
        return (len(self.document.xpath('//div[@class="no-records"]')) == 0)
