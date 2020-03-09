# -*- coding: utf-8 -*-

# Copyright(C) 2018      Simon Rochwerg
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

import re

from weboob.browser.pages import HTMLPage, LoggedPage, RawPage
from weboob.browser.elements import method, ItemElement, ListElement
from weboob.browser.filters.standard import (
    CleanText, CleanDecimal, Currency, Date, NumberFormatError,
    Field, Env, MapIn,
)
from weboob.capabilities.base import NotAvailable, empty
from weboob.capabilities.bank import Account, Transaction, Investment, PerVersion
from weboob.browser.filters.html import Attr
from weboob.capabilities.profile import Profile
from weboob.tools.capabilities.bank.investments import IsinCode, IsinType


class LoginPage(HTMLPage):
    def login(self, login, password):
        form = self.get_form('//form[@class="form-horizontal"]')
        form['Login'] = login
        form['Password'] = password
        form.submit()


class ErrorPage(HTMLPage):
    def get_error(self):
        alert = CleanText('//td/div[@class="editorialContent"]|//div[has-class("blockMaintenance")]/table//p[contains(text(), "password")]')(self.doc)
        if alert:
            return alert


class ProfilePage(LoggedPage, HTMLPage):
    @method
    class get_profile(ItemElement):
        klass = Profile

        obj_name = CleanText('//*[@id="navAffiliationInfos"]/ul/li[1]')
        obj_address = CleanText('//*[@id="1a"]/div[2]/div/div[1]/span')
        obj_email = Attr('//*[@id="Email"]', 'value')


class TermPage(HTMLPage):
    pass


class UnexpectedPage(HTMLPage):
    def get_error(self):
        alert = CleanText('//div[@class="blockMaintenance mainBlock"]/table//td/h3')(self.doc)
        if alert:
            return alert


class AccountPage(LoggedPage, HTMLPage):
    ACCOUNT_TYPES = {
        'PER ': Account.TYPE_PER,
    }

    @method
    class iter_accounts(ListElement):
        item_xpath = '//div[@id="desktop-data-tables"]/table//tr'

        def store(self, obj):
            # This code enables indexing account_id when there
            # are several accounts with the exact same id.
            id = obj.id
            n = 1
            while id in self.objects:
                n += 1
                id = '%s-%s' % (obj.id, n)
            obj.id = id
            self.objects[obj.id] = obj
            return obj

        class item(ItemElement):
            klass = Account

            def obj_id(self):
                _id = CleanText('./td[1]')(self)
                _id = ''.join(i for i in _id if i.isdigit())
                return _id

            obj_number = obj_id
            obj_label = CleanText('./td[2]', replace=[(' o ', ' ')])
            obj_currency = Currency('./td[6]')
            obj_company_name = CleanText('./td[3]')

            def obj__sublabel(self):
                # Use the second part of the label to determine account index
                # later on InvestmentPage and remove the 'N ' at the beginning
                sublabel = CleanText('./td[2]', children=False)(self)
                if sublabel.startswith('N '):
                    sublabel = sublabel[2:]
                return sublabel

            def obj_type(self):
                return MapIn(Field('label'), self.page.ACCOUNT_TYPES, Account.TYPE_UNKNOWN)(self)

            def obj_balance(self):
                # This wonderful website randomly displays separators as '.' or ','
                # For example, numbers can look like "€12,345.67" or "12 345,67 €"
                try:
                    return CleanDecimal.French('./td[6]')(self)
                except NumberFormatError:
                    return CleanDecimal.US('./td[6]')(self)

    PER_VERSIONS = {
        'Entreprises': PerVersion.PERCOL,
    }

    @method
    class fill_per(ItemElement):
        def obj_version(self):
            return MapIn(self, self.page.PER_VERSIONS, NotAvailable).filter(self.obj.label)


class AccountSwitchPage(LoggedPage, RawPage):
    # This page is empty (only two blank lines)
    # so we have to handle it with RawPage
    pass


class HistoryPage(LoggedPage, HTMLPage):
    @method
    class iter_history(ListElement):
        item_xpath = '//div[@class="accordion_container"]//div[@class="accordion_head-container"]'

        class item(ItemElement):
            klass = Transaction

            obj_date = Date(CleanText('./div[contains(@class, "accordion_header")]/div[1]/p'))
            obj_category = CleanText('./div[contains(@class, "accordion_header")]/div[2]/p[1]')
            obj_label = CleanText('./div[contains(@class, "accordion_header")]/div[3]/p[1]')
            obj_type = Transaction.TYPE_BANK

            def obj_amount(self):
                # This wonderful website randomly displays separators as '.' or ','
                # For example, numbers can look like "€12,345.67" or "12 345,67 €"
                try:
                    return CleanDecimal.French('./div[contains(@class, "accordion_header")]/div[position()=last()]')(self)
                except NumberFormatError:
                    return CleanDecimal.US('./div[contains(@class, "accordion_header")]/div[position()=last()]')(self)


class InvestmentPage(LoggedPage, HTMLPage):
    @method
    class iter_investments(ListElement):
        item_xpath = '//div[contains(@class, "table-lg-container")]//tr'

        class item(ItemElement):
            klass = Investment

            def parse(self, obj):
                # This wonderful website randomly displays separators as '.' or ','
                # For example, numbers can look like "€12,345.67" or "12 345,67 €"
                if '.' in CleanText('./td[4]')(self):
                    # American format
                    self.env['quantity'] = CleanDecimal.US('./td[2]', default=NotAvailable)(self)
                    self.env['unitvalue'] = CleanDecimal.US('./td[3]', default=NotAvailable)(self)
                    self.env['valuation'] = CleanDecimal.US('./td[4]')(self)
                else:
                    # French format
                    self.env['quantity'] = CleanDecimal.French('./td[2]', default=NotAvailable)(self)
                    self.env['unitvalue'] = CleanDecimal.French('./td[3]', default=NotAvailable)(self)
                    self.env['valuation'] = CleanDecimal.French('./td[4]')(self)

            obj_label = CleanText('.//p[contains(@class, "support-label")]')
            obj_code = IsinCode(CleanText('.//p[contains(@class, "code-isin")]'), default=NotAvailable)
            obj_code_type = IsinType(Field('code'))
            obj_quantity = Env('quantity')
            obj_unitvalue = Env('unitvalue')
            obj_valuation = Env('valuation')

    def get_account_index(self, sublabel):
        # From the <li> tag that contains the sublabel, we fetch the
        # account index from a string such as 'changeAffiliation(2)':
        raw_index = Attr('//li[span[contains(text(), "%s")]]' % sublabel, 'onclick', default=None)(self.doc)
        assert not empty(raw_index), 'Could not find the index to access investments for account %s.' % sublabel
        m = re.search(r'\d+', raw_index)
        assert m, 'Could not extract the index to access investments for account %s.' % sublabel
        return m.group(0)
