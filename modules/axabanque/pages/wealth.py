# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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

from weboob.browser.pages import HTMLPage, LoggedPage, pagination
from weboob.browser.elements import ListElement, ItemElement, method, TableElement
from weboob.browser.filters.standard import (
    CleanText, Date, Regexp, CleanDecimal, Eval, Field, Async, AsyncLoad,
    TableCell, QueryValue, Currency
)
from weboob.browser.filters.html import Attr, Link
from weboob.capabilities.bank import Account, Investment
from weboob.capabilities.base import NotAvailable, NotLoaded
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)


class AccountsPage(LoggedPage, HTMLPage):
    TYPES = {u'assurance vie': Account.TYPE_LIFE_INSURANCE,
             u'perp': Account.TYPE_PERP,
             u'novial avenir': Account.TYPE_MADELIN,
            }

    @method
    class iter_accounts(ListElement):
        item_xpath = '//section[has-class("contracts")]/article'

        class item(ItemElement):
            klass = Account

            condition = lambda self: Field('balance')(self) is not NotAvailable

            obj_id = Regexp(CleanText('.//h2/small'), '(\d+)')
            obj_label = CleanText('.//h2/text()')
            obj_balance = MyDecimal('.//span[has-class("card-amount")]')
            obj_valuation_diff = MyDecimal('.//p[@class="card-description"]')
            obj_url = Attr('.', 'data-redirect')
            obj__acctype = "investment"

            def obj_type(self):
                types = [v for k, v in self.page.TYPES.items() if k in Field('label')(self).lower()]
                return types[0] if len(types) else Account.TYPE_UNKNOWN

            def obj_currency(self):
                return Account.get_currency(CleanText('.//span[has-class("card-amount")]')(self))


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


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(u'^(?P<text>souscription.*)'), FrenchTransaction.TYPE_DEPOSIT),
                (re.compile(u'^(?P<text>.*)'), FrenchTransaction.TYPE_BANK),
               ]


class HistoryPage(LoggedPage, HTMLPage):
    def build_doc(self, content):
        # we got empty pages at end of pagination
        if not content.strip():
            content = b"<html></html>"
        return super(HistoryPage, self).build_doc(content)

    def get_account_url(self, url):
        return Attr(u'//a[@href="%s"]' % url, 'data-target')(self.doc)

    def get_investment_url(self):
        return Attr('//article[has-class("card-distribution")]', 'data-url', default=None)(self.doc)

    def get_pagination_url(self):
        return Attr('//div[contains(@class, "default")][@data-current-page]', 'data-url')(self.doc)

    @method
    class get_investments(ListElement):
        item_xpath = '//div[@class="white-bg"][.//strong[contains(text(), "support")]]/following-sibling::div'

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText('.//div[has-class("t-data__label")]')
            obj_valuation = MyDecimal('.//div[has-class("t-data__amount") and has-class("desktop")]')
            obj_portfolio_share = Eval(lambda x: x / 100, CleanDecimal('.//div[has-class("t-data__amount_label")]'))

    @pagination
    @method
    class iter_history(ListElement):
        item_xpath = '//div[contains(@data-url, "savingsdetailledcard")]'

        def next_page(self):
            if not CleanText(self.item_xpath, default=None)(self):
                return
            elif self.env.get('no_pagination'):
                return

            return re.sub(r'(?<=\bskip=)(\d+)', lambda m: str(int(m.group(1)) + 10), self.page.url)

        class item(ItemElement):
            klass = Transaction

            load_details = Attr('.', 'data-url') & AsyncLoad

            obj_raw = Transaction.Raw('.//div[has-class("desktop")]//em')
            obj_date = Date(CleanText('.//div[has-class("t-data__date") and has-class("desktop")]'), dayfirst=True)
            obj_amount = MyDecimal('.//div[has-class("t-data__amount") and has-class("desktop")]')

            def obj_investments(self):
                investments = list(Async('details').loaded_page(self).get_investments())
                for inv in investments:
                    inv.vdate = Field('date')(self)
                return investments
