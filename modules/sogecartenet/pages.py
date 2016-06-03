# -*- coding: utf-8 -*-

# Copyright(C) 2015 Vincent Paredes
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

import requests

from weboob.browser.pages import HTMLPage, CsvPage, pagination
from weboob.exceptions import BrowserIncorrectPassword, BrowserPasswordExpired
from weboob.browser.elements import DictElement, ItemElement, method, TableElement
from weboob.browser.filters.standard import CleanText, CleanDecimal, Date, Env, TableCell
from weboob.browser.filters.json import Dict
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction

__all__ = ['LoginPage', 'AccountsPage', 'TransactionsPage']


class PassModificationPage(HTMLPage):
    def on_load(self):
        raise BrowserPasswordExpired('New pass needed')

class LoginPage(HTMLPage):
    pass

class SogeLoggedPage(object):
    @property
    def logged(self):
        if hasattr(self.doc, 'xpath'):
            return not self.doc.xpath('//input[@value="LOGIN"][@name="QUEFAIRE"]')
        return True

    def on_load(self):
        if hasattr(self.doc, 'xpath') and self.doc.xpath('//input[@value="LOGIN"][@name="QUEFAIRE"]'):
            raise BrowserIncorrectPassword()

class AccountsPage(SogeLoggedPage, HTMLPage):
    @pagination
    @method
    class iter_accounts(TableElement):
        item_xpath = '//table[@bgcolor="#92ADC2"]//tr'
        head_xpath = '//table[@bgcolor="#92ADC2"]/tr[1]/td[text()]'

        col_id = 'card iconetriwbeb(2);'
        col_label = 'name iconetriwbeb(1);'

        def next_page(self):
            array_page = self.page.doc.xpath('//table[3]')[0]
            if array_page.xpath('.//a[@href="javascript:fctSuivant();"]'):
                curr_page = CleanDecimal().filter(array_page.xpath('.//td')[3].text)
                data = {'PAGE': curr_page, 'QUEFAIRE':'NEXT', 'TRI':'ACC', 'TYPEDETAIL':'C'}
                return requests.Request("POST", self.page.url, data=data)
            return

        class item(ItemElement):
            klass = Account

            obj_id = CleanText(TableCell('id'), replace=[(' ', ''), ('X','')])
            obj_label = CleanText(TableCell('label'))
            obj_type = Account.TYPE_CARD

            @property
            def obj__url(self):
                a = self.el.xpath('.//a')
                if a and len(a) > 1:
                     #handling relative path
                    return '%s/%s' % ('/'.join(self.page.url.split('/')[:-1]), a[-1].attrib['href'][2:])
                return None

            def condition(self):
                 return self.el.xpath('./td[@bgcolor="#FFFFFF"]')

class TransactionsPage(SogeLoggedPage, CsvPage):
    ENCODING = 'iso_8859_1'
    HEADER = 1
    FMTPARAMS = {'delimiter':';'}
    @method
    class get_history(DictElement):
        class item(ItemElement):
            klass = FrenchTransaction

            obj_rdate = Date(CleanText(Dict('Processing date')))
            obj_date = Date(CleanText(Dict('Transaction date')))
            obj_raw = FrenchTransaction.Raw(CleanText(Dict('corporate name')))
            obj_amount = FrenchTransaction.Amount(CleanText(Dict('charged amt')), replace_dots=False)
            obj_original_amount = FrenchTransaction.Amount(CleanText(Dict('orig. currency gross amt')), replace_dots=False)
            obj_original_currency = CleanText(Dict('orig. currency code'))
            obj_country = CleanText(Dict('country cde'))

            def condition(self):
                return False

            def has_data(self):
                return not Dict().filter(self.el)['processing date'] == u'No data found'

            def check_debit(self):
                return Dict().filter(self.el)['debit / credit'] == 'D'

        class credit(item):
            def condition(self):
                return self.has_data() and not self.check_debit()

        class debit(item):

            obj_amount = FrenchTransaction.Amount(CleanText(Env('amount')), replace_dots=False)
            obj_original_amount = FrenchTransaction.Amount(CleanText(Env('original_amount')), replace_dots=False)

            def condition(self):
                if self.has_data() and self.check_debit():
                    self.env['amount'] = "-" + self.el['charged amt']
                    self.env['original_amount'] = "-" + self.el['orig. currency gross amt']
                    return True
                return False
