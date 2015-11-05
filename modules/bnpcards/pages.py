# -*- coding: utf-8 -*-

# Copyright(C) 2015      Baptiste Delpey
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

import re
from datetime import date

from weboob.browser.pages import HTMLPage, LoggedPage, pagination
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import CleanText, CleanDecimal, Field
from weboob.browser.filters.html import Link
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


class HomePage(LoggedPage, HTMLPage):
    def is_corporate(self):
        el = self.doc.xpath('//div[@class="marges5"]/h5/a[contains(text(), "CORPORATE")]')
        if el:
            return True

    def is_error(self):
        if self.doc.xpath('//h1[contains(text(), "Change your password")]'):
            return True


class LoginPage(HTMLPage):
    def login(self, type, username, password):
        form = self.get_form(name='connecterForm')
        form['type'] = type
        form['login'] = username
        form['pwd'] = password[:8]
        form.url = '/ce_internet_public/seConnecter.event.do'
        form.submit()


class ExpandablePage(LoggedPage, HTMLPage):
    def expand(self):
        form = self.get_form()
        form.submit()


class GetableLinksPage(LoggedPage, HTMLPage):
    def get_link(self, account_id):
        el = self.doc.xpath('.//a[contains(text(), "%s")]' % account_id)
        if not el:
            return
        return el[0].get("href")


class PeriodsPage(LoggedPage, HTMLPage):
    def get_periods(self):
        periods = []
        for period in self.doc.xpath('//select[@name="periodeSaisie"]/option/@value'):
            periods.append(period)
        return periods

    def expand(self, period):
        form = self.get_form(submit='//input[@value="Display"]')
        form['bouton'] = 'rechercher'
        form['periodeSaisie'] = period
        form['periodeSaisieCache'] = period
        form.submit()


class AccountsPage(ExpandablePage, GetableLinksPage):
    @pagination
    @method
    class iter_accounts(ListElement):
        item_xpath = '//table[@id="datas"]/tbody/tr'

        next_page = Link('//table[@id="datas"]/tfoot//b/following-sibling::a[1]')

        class item(ItemElement):
            klass = Account

            obj_id = CleanText('./td[2]')
            obj_label = CleanText('./td[1]')
            obj_type = Account.TYPE_CARD


class ComingPage(ExpandablePage):
    def get_link(self, account_id):
        el = self.doc.xpath('.//a[contains(text(), "%s")]' % account_id)
        if not el:
            return
        link = re.search(r",'(.*)'\);", el[0].get("href"))
        if link:
            return link.group(1)


class HistoPage(GetableLinksPage, PeriodsPage):
    pass


class TransactionsPage(LoggedPage, HTMLPage):
    @pagination
    @method
    class get_history(ListElement):
        item_xpath = '//table[@id="datas"]/tbody/tr'
        next_page = Link('//table[@id="datas"]/tfoot//b/following-sibling::a[1]')

        class item(ItemElement):
            klass = FrenchTransaction

            obj_rdate = FrenchTransaction.Date(CleanText('./td[1]'))
            obj_date = FrenchTransaction.Date(CleanText('./td[3]'))
            obj_raw = FrenchTransaction.Raw(CleanText('./td[2]'))
            _obj_amnt = FrenchTransaction.Amount(CleanText('./td[5]'), replace_dots=False)
            obj_original_amount = FrenchTransaction.Amount(CleanText('./td[4]'), replace_dots=False)
            obj_original_currency = FrenchTransaction.Currency(CleanText('./td[4]'))
            obj_commission = FrenchTransaction.Amount(CleanText('./td[6]'), replace_dots=False)

            def obj__coming(self):
                if Field('date')(self) >= date.today():
                    return True
                return

            def obj_amount(self):
                if not Field('obj_commission'):
                    return Field('_obj_amnt')
                else:
                    return CleanDecimal(replace_dots=False).filter(self.el.xpath('./td[5]')) - CleanDecimal(replace_dots=False).filter(self.el.xpath('./td[6]'))


class ErrorPage(HTMLPage):
    pass


class TiCardPage(ExpandablePage, TransactionsPage):
    @method
    class iter_accounts(ListElement):
        item_xpath = '//table[@class="params"]/tr'
        class item(ItemElement):
            klass = Account
            obj_id = CleanText('./td[2]/select/option', replace=[(' ', '')])
            obj_label = CleanText('./td[1]/b[2]')
            obj_type = Account.TYPE_CARD


class TiHistoPage(PeriodsPage, TransactionsPage):
    pass
