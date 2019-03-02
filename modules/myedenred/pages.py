# -*- coding: utf-8 -*-

# Copyright(C) 2017      Théo Dorée
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals


from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.elements import ItemElement, method, ListElement
from weboob.browser.filters.standard import (
    CleanText, CleanDecimal,
    Regexp, DateGuesser, Field
)
from weboob.capabilities.bank import Account, Transaction
from weboob.capabilities.base import NotAvailable
from weboob.tools.date import LinearDateGuesser
from datetime import timedelta


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)


class LoginPage(HTMLPage):
    def get_error(self):
        return CleanText('//li[@class="notification-summary-message-error"][1]')(self.doc)


class AccountsPage(LoggedPage, HTMLPage):
    @method
    class iter_accounts(ListElement):
        item_xpath = '//ul[@id="navSideProducts"]/li'

        class item(ItemElement):
            klass = Account

            obj_type = Account.TYPE_CARD
            obj_id = CleanText('./a/p', replace=[('N° ', '')])
            obj_label = obj_id
            obj_currency = u'EUR'
            obj_balance = MyDecimal(u'//p[@class="num"]//strong')

            # Every subscription a product token and a type ex: card = 240
            obj__product_token = Regexp(CleanText('./@id'), r'navSideProduct_(\d*)')
            obj__product_type = Regexp(CleanText('(//div[@class="logo"])[1]//img/@src'), "/img/product_(\d*).png")


class TransactionsPage(LoggedPage, HTMLPage):
    @method
    class iter_transactions(ListElement):
        item_xpath = '(//table[contains(@class, "table-transaction")])[1]/tbody/tr'

        class item(ItemElement):
            klass = Transaction

            obj_date = DateGuesser(CleanText('.//span[contains(., "/")]'), LinearDateGuesser(date_max_bump=timedelta(45)))
            obj_label = CleanText('.//h3/strong')
            obj_raw = Field('label')
            obj_amount = MyDecimal('./td[@class="al-r"]/div/span[has-class("badge")]')
            def obj_type(self):
                amount = Field('amount')(self)
                if amount < 0:
                    return Transaction.TYPE_CARD
                else:
                    return Transaction.TYPE_TRANSFER
