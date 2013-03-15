# -*- coding: utf-8 -*-

# Copyright(C) 2013 Romain Bignon
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


import datetime
from decimal import Decimal
import re
from mechanize import FormNotFoundError

from weboob.tools.browser import BasePage, BrowserIncorrectPassword
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


__all__ = ['LoginPage', 'AccountsPage', 'TransactionsPage']


class LoginPage(BasePage):
    def redirect(self):
        try:
            self.browser.select_form(name='redirectEpargne')
            self.browser.submit(nologin=True)
        except FormNotFoundError:
            raise BrowserIncorrectPassword()


class HomePage(BasePage):
    pass


class AccountsPage(BasePage):
    def get_list(self):
        div = self.document.xpath('//div[@id="descriptifdroite"]')[0]

        account = Account()

        account.id = re.search(u'(\d+)', div.xpath('.//div[@class="credithauttexte"]')[0].text).group(1)
        account.label = u'Carte PASS'
        account.balance = Decimal('0')

        for tr in div.xpath('.//table/tr'):
            tds = tr.findall('td')

            if len(tds) < 3:
                continue

            label = u''.join([txt.strip() for txt in tds[1].itertext()])
            value = u''.join([txt.strip() for txt in tds[2].itertext()])

            if 'encours depuis le dernier' in label.lower():
                coming = u'-' + value
                account.coming = Decimal(FrenchTransaction.clean_amount(coming))
                account.currency = account.get_currency(coming)
            elif u'arrêté de compte' in label.lower():
                m = re.search(u'(\d+)/(\d+)/(\d+)', label)
                if m:
                    account._outstanding_date = datetime.date(*reversed(map(int, m.groups())))
                    break

        yield account


class TransactionsPage(BasePage):
    COL_DATE = 0
    COL_TEXT = 1
    COL_AMOUNT = 2

    def get_history(self, account):
        transactions = []
        last_order = None

        for tr in self.document.split('\n')[1:]:
            cols = tr.split(';')

            if len(cols) < 4:
                continue

            t = FrenchTransaction(0)
            date = cols[self.COL_DATE]
            raw = cols[self.COL_TEXT]
            amount = cols[self.COL_AMOUNT]

            t.parse(date, re.sub(r'[ ]+', ' ', raw))

            if t.raw.startswith('PRELEVEMENT ACHATS DIFFERES'):
                t._coming = False
                if last_order is None:
                    last_order = t.date
            else:
                t._coming = True

            t.set_amount(amount)
            transactions.append(t)

        # go to the previous stop date before the last order
        while last_order is not None and last_order.day != account._outstanding_date.day:
            last_order = last_order - datetime.timedelta(days=1)

        for t in transactions:
            if t.date <= last_order:
                t._coming = False

        return iter(transactions)
