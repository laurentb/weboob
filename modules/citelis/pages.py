# -*- coding: utf-8 -*-

# Copyright(C) 2013      Laurent Bachelier
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

from weboob.tools.browser import BasePage
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


__all__ = ['LoginPage', 'SummaryPage', 'UselessPage']


class Transaction(FrenchTransaction):
    @classmethod
    def clean_amount(cls, text):
        text = text.strip()
        # Convert "American" UUU.CC format to "French" UUU,CC format
        if re.search(r'\d\.\d\d$', text):
            text = text.replace(',', ' ').replace('.', ',')
        return FrenchTransaction.clean_amount(text)


class LoginPage(BasePage):
    def login(self, merchant_id, login, password):
        self.browser.select_form(name='loginForm')
        self.browser['merchant'] = merchant_id.encode(self.browser.ENCODING)
        self.browser['login'] = login.encode(self.browser.ENCODING)
        self.browser['password'] = password.encode(self.browser.ENCODING)
        self.browser.submit()


class SummaryPage(BasePage):
    def clean_amount(self, el, debit):
        amount = Decimal(Transaction.clean_amount(el.text_content()))
        if amount == Decimal('0.00'):
            return None
        if debit and amount > Decimal('0'):
            return -1 * amount
        return amount

    def get_balance(self):
        zone = self.parser.select(self.document.getroot(), '#ActionZone_Euro', 1)
        for tr in self.parser.select(zone, '#transactionError tr'):
            tds = self.parser.select(tr, 'td')
            if tds and tds[0].text_content().strip() == 'Total':
                debit, credit = self.parser.select(tr, 'td.amount', 4)[-2:]  # keep the last 2
                debit = self.clean_amount(debit, debit=True)
                credit = self.clean_amount(credit, debit=False)
                amount = credit or debit
                return amount


class UselessPage(BasePage):
    pass
