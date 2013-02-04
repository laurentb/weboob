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

from weboob.tools.browser import BasePage
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction

__all__ = ['LoginPage', 'AccountPage']


class LoginPage(BasePage):
    def login(self, login, password):
        self.browser.select_form(name='login_form')
        self.browser['login_email'] = login
        self.browser['login_password'] = password
        self.browser.submit(nologin=True)


class AccountPage(BasePage):
    def get_account(self):
        account = Account()
        account.id = u"1"
        account.label = unicode(self.browser.username)
        account.type = Account.TYPE_CHECKING

        balance = self.document.xpath('//div[@id="main"]')[0] \
            .xpath('.//div[@class="col first"]//h3/span[@class="balance"]')[0] \
            .balance.text_content().strip()
        account.balance = Decimal(FrenchTransaction.clean_amount(balance))
        account.currency = account.get_currency(balance)

        return account
