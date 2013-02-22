# -*- coding: utf-8 -*-

# Copyright(C) 2009-2011  Romain Bignon, Florent Fourcot
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

from weboob.capabilities.bank import Account, Currency
from weboob.capabilities.base import NotAvailable
from weboob.tools.browser import BasePage, BrowserUnavailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


__all__ = ['AccountsList']


class AccountsList(BasePage):
    def on_loaded(self):
        pass

    def get_list(self):
        # TODO: no idea abount how proxy account are displayed
        for a in self.document.xpath('//a[@class="mainclic"]'):
            account = Account()
            account.currency = Currency.CUR_EUR
            account.id = unicode(a.find('span[@class="account-number"]').text)
            account.label = unicode(a.find('span[@class="title"]').text)
            balance = a.find('span[@class="solde"]/label').text
            account.balance = Decimal(FrenchTransaction.clean_amount(balance))
            account.coming = NotAvailable
            if "Courant" in account.label:
                account.id = "CC-" + account.id
            elif "Livret A" in account.label:
                account.id = "LA-" + account.id
            elif "Orange" in account.label:
                account.id = "LEO-" + account.id
            yield account
