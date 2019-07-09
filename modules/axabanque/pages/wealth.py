# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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

from decimal import Decimal
from weboob.browser.pages import HTMLPage, LoggedPage, JsonPage
from weboob.browser.elements import ListElement, DictElement, ItemElement, method, TableElement
from weboob.browser.filters.standard import (
    CleanDecimal, CleanText, Currency, Date, Eval, Field, Lower, MapIn, QueryValue, Regexp,
)
from weboob.browser.filters.html import Attr, Link, TableCell
from weboob.browser.filters.json import Dict
from weboob.capabilities.bank import Account, Investment
from weboob.capabilities.profile import Person
from weboob.capabilities.base import NotAvailable, NotLoaded
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


def float_to_decimal(f):
    return Decimal(str(f))


class AccountsPage(LoggedPage, HTMLPage):
    @method
    class iter_accounts(ListElement):
        item_xpath = '//div[contains(@data-route, "/savings/")]'

        class item(ItemElement):
            klass = Account

            TYPES = {u'assurance vie': Account.TYPE_LIFE_INSURANCE,
                     u'perp': Account.TYPE_PERP,
                     u'epargne retraite agipi pair': Account.TYPE_PERP,
                     u'epargne retraite agipi far': Account.TYPE_MADELIN,
                     u'novial avenir': Account.TYPE_MADELIN,
                     u'epargne retraite novial': Account.TYPE_LIFE_INSURANCE,
                    }

            condition = lambda self: Field('balance')(self) is not NotAvailable

            obj_id = Regexp(CleanText('.//span[has-class("small-title")]'), r'([\d/]+)')
            obj_label = CleanText('.//h3[has-class("card-title")]')
            obj_balance = CleanDecimal.French('.//p[has-class("amount-card")]')
            obj_valuation_diff = CleanDecimal.French('.//p[@class="performance"]', default=NotAvailable)

            def obj_url(self):
                url = Attr('.', 'data-route')(self)
                # The Assurance Vie xpath recently changed so we must verify that all
                # the accounts now have "/savings/" instead of "/assurances-vie/".
                assert "/savings/" in url
                return url

            obj_currency = Currency('.//p[has-class("amount-card")]')
            obj__acctype = "investment"

            obj_type = MapIn(Lower(Field('label')), TYPES, Account.TYPE_UNKNOWN)


class InvestmentPage(LoggedPage, HTMLPage):
    @method
    class iter_investment(TableElement):
        item_xpath = '//table/tbody/tr[td[2]]'
        head_xpath = '//table/thead//th'

        col_label = 'Nom des supports'
        col_valuation = re.compile('.*Montant')
        col_vdate = 'Date de valorisation'
        col_portfolio_share = u'Répartition'
        col_quantity = re.compile('Nombre de parts')
        col_unitvalue = re.compile('Valeur de la part')

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(TableCell('label'))
            obj_code = QueryValue(Link('.//a[contains(@href, "isin")]', default=''), 'isin', default=NotAvailable)

            def valuation(self):
                td = TableCell('valuation')(self)[0]
                return CleanDecimal('.')(td)

            def obj_quantity(self):
                if not self.page.is_detail():
                    return NotAvailable
                td = TableCell('quantity')(self)[0]
                return CleanDecimal('.//span[1]', replace_dots=True)(td)

            def obj_valuation(self):
                if self.obj_original_currency():
                    return NotAvailable
                return self.valuation()

            def obj_original_valuation(self):
                if self.obj_original_currency():
                    return self.valuation()
                return NotLoaded

            def obj_vdate(self):
                td = TableCell('vdate')(self)[0]
                txt = CleanText('./text()')(td)
                return Date('.', dayfirst=True, default=NotAvailable).filter(txt)

            def obj_code_type(self):
                lst = self.el.xpath('./th/a')
                if not lst:
                    return NotAvailable
                return Investment.CODE_TYPE_ISIN

            obj_code = Regexp(Link('./th/a', default=''), r'isin=(.{12})$', default=NotAvailable)

            def unitvalue(self):
                return CleanDecimal(TableCell('unitvalue'), replace_dots=True)(self)

            def obj_unitvalue(self):
                if not self.page.is_detail() or self.obj_original_currency():
                    return NotAvailable
                return self.unitvalue()

            def obj_original_unitvalue(self):
                if self.page.is_detail() and self.obj_original_currency():
                    return self.unitvalue()
                return NotLoaded

            def obj_portfolio_share(self):
                if self.page.is_detail():
                    return NotAvailable
                return Eval(lambda x: x / 100, CleanDecimal(TableCell('portfolio_share'), replace_dots=True))(self)

            def obj_original_currency(self):
                cur = Currency(TableCell('valuation'))(self)
                return cur if self.env['currency'] != cur else NotLoaded

    def detailed_view(self):
        return Attr(u'//button[contains(text(), "Vision détaillée")]', 'data-url', default=None)(self.doc)

    def is_detail(self):
        return bool(self.doc.xpath(u'//th[contains(text(), "Valeur de la part")]'))


class AccountDetailsPage(LoggedPage, HTMLPage):
    def get_account_url(self, url):
        return Attr('//a[@href="%s"]' % url, 'data-target')(self.doc)

    def get_investment_url(self):
        return Attr('//div[has-class("card-distribution")]', 'data-url', default=None)(self.doc)


class Transaction(FrenchTransaction):
    PATTERNS = [
        (re.compile('^(?P<text>souscription.*)'), FrenchTransaction.TYPE_DEPOSIT),
        (re.compile('^(?P<text>.*)'), FrenchTransaction.TYPE_BANK),
    ]


class HistoryPage(LoggedPage, JsonPage):
    @method
    class iter_history(DictElement):

        class item(ItemElement):
            klass = Transaction

            obj_raw = Transaction.Raw(Dict('label'))
            obj_date = Date(Dict('date'))
            obj_amount = Eval(float_to_decimal, Dict('gross_amount/value'))

            def validate(self, obj):
                return CleanText(Dict('status'))(self) == 'DONE'

    def get_error_code(self):
        # The server returns a list if it worked and a dict in case of error
        if isinstance(self.doc, dict) and 'return' in self.doc:
            return self.doc['return']['error']['code']
        return None


class ProfilePage(LoggedPage, HTMLPage):
    def get_profile(self):
        form = self.get_form(xpath='//div[@class="popin-card"]')

        profile = Person()

        profile.name = '%s %s' % (form['party.first_name'], form['party.preferred_last_name'])
        profile.address = '%s %s %s' % (form['mailing_address.street_line'], form['mailing_address.zip_postal_code'], form['mailing_address.locality'])
        profile.email = CleanText('//label[@class="email-editable"]')(self.doc)
        profile.phone = CleanText('//div[@class="info-title colorized phone-disabled"]//label', children=False)(self.doc)
        return profile
