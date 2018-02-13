# -*- coding: utf-8 -*-

# Copyright(C) 2017      Tony Malto
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

from __future__ import unicode_literals

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.elements import ItemElement, method, ListElement
from weboob.capabilities.bank import Account
from weboob.browser.filters.standard import CleanText, CleanDecimal, Currency
from weboob.capabilities.base import NotAvailable


class LoginPage(HTMLPage):
    def login(self, login, password):
        form = self.get_form('//form[@action="/j_security_check"]')
        form['j_username'] = login
        form['j_password'] = password
        form.submit()

    def get_error(self):
        return CleanText('//div[contains(text(), "Erreur")]')(self.doc)


class AccountsPage(LoggedPage, HTMLPage):
    @method
    class iter_accounts(ListElement):
        item_xpath = '//div[@class="bk-contrat theme-epargne"]'

        class item(ItemElement):
            klass = Account

            obj_id = CleanText('.//div[@class="infos-contrat"]//strong')
            obj_label = CleanText('.//div[@class="type-contrat"]//h2')
            obj_type = Account.TYPE_LIFE_INSURANCE
            obj_balance = CleanDecimal(CleanText('.//div[@class="col-right"]', children=False), replace_dots=True, default=NotAvailable)
            obj_currency = Currency(CleanText(u'.//div[@class="col-right"]', children=False, replace=[("Au", "")]))
