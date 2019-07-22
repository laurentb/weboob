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

from weboob.browser.pages import HTMLPage, PartialHTMLPage, LoggedPage
from weboob.browser.elements import ItemElement, method, ListElement
from weboob.browser.filters.standard import (
    CleanText, CleanDecimal,
    Regexp, DateGuesser, Field, Env
)
from weboob.capabilities.bank import Account, Transaction
from weboob.capabilities.base import NotAvailable


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)


class LoginPage(HTMLPage):
    def get_error(self):
        return CleanText('//li[@class="notification-summary-message-error"][1]')(self.doc)


class AccountsPage(LoggedPage, HTMLPage):
    def get_accounts_id(self):
        for e in self.doc.xpath('//ul[@id="navSideProducts"]//strong[contains(text(), "Restaurant")]/ancestor::li'):
            yield e.attrib['id'].split('_')[-1]


class AccountDetailsPage(LoggedPage, PartialHTMLPage):
    @method
    class get_account(ItemElement):
        klass = Account

        obj_type = Account.TYPE_CARD
        obj_id = CleanText('//p[contains(text(), "Identifiant")]/a')
        obj_label = obj_id
        obj_currency = u'EUR'
        obj_balance = MyDecimal('//p[@class="num"]/a')
        obj_cardlimit = MyDecimal('//div[has-class("solde_actu")]')

        # Every subscription a product token and a type ex: card = 240
        obj__product_token = Regexp(CleanText('//div[contains(@id, "product")]/@id'), r'productLine_(\d*)')
        obj__product_type = Regexp(CleanText('(//div[@class="logo"])[1]//img/@src'), "/img/product_(\d*).png")



class TransactionsPage(LoggedPage, HTMLPage):
    @method
    class iter_transactions(ListElement):
        item_xpath = '(//table[contains(@class, "table-transaction")])[1]/tbody/tr'

        class item(ItemElement):
            klass = Transaction

            def condition(self):
                return CleanText('./td[@class="al-c"]/span')(self) not in ('transaction refusée', 'transaction en cours de traitement')

            obj_date = DateGuesser(CleanText('.//span[contains(., "/")]'), Env('date_guesser'))
            obj_label = CleanText('.//h3/strong')
            obj_raw = Field('label')
            obj_amount = MyDecimal('./td[@class="al-r"]/div/span[has-class("badge")]')

            def obj_type(self):
                amount = Field('amount')(self)
                if amount < 0:
                    return Transaction.TYPE_CARD
                else:
                    return Transaction.TYPE_TRANSFER
