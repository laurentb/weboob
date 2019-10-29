# -*- coding: utf-8 -*-

# Copyright(C) 2012-2019  Budget Insight
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
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import (
    CleanText, Title, Format, Date, Regexp, CleanDecimal, Env,
    Currency, Field, Eval, Coalesce,
)
from weboob.capabilities.bank import Investment, Transaction
from weboob.capabilities.base import NotAvailable
from weboob.exceptions import ActionNeeded, BrowserUnavailable
from weboob.tools.compat import urljoin
from weboob.tools.capabilities.bank.investments import IsinCode, IsinType


class BasePage(HTMLPage):
    def on_load(self):
        super(BasePage, self).on_load()

        if 'Erreur' in CleanText('//div[@id="main"]/h1', default='')(self.doc):
            err = CleanText('//div[@id="main"]/div[@class="content"]', default='Site indisponible')(self.doc)
            raise BrowserUnavailable(err)


class PrevoyancePage(LoggedPage, HTMLPage):
    pass


class LoginPage(BasePage):
    def login(self, login, password):
        form = self.get_form(id="loginForm")
        form['username'] = login
        form['password'] = password
        form.submit()


class MigrationPage(LoggedPage, HTMLPage):
    def get_error(self):
        return CleanText('//h1[contains(text(), "Votre nouvel identifiant et mot de passe")]')(self.doc)


class InvestmentPage(LoggedPage, HTMLPage):
    @method
    class fill_account(ItemElement):
        obj_balance = CleanDecimal.French('//ul[has-class("m-data-group")]//strong')
        obj_currency = Currency('//ul[has-class("m-data-group")]//strong')
        obj_valuation_diff = CleanDecimal.French('//h3[contains(., "value latente")]/following-sibling::p[1]', default=NotAvailable)

    def get_history_link(self):
        history_link = self.doc.xpath('//li/a[contains(text(), "Historique")]/@href')
        return urljoin(self.browser.BASEURL, history_link[0]) if history_link else ''

    def unavailable_details(self):
        return CleanText('//p[contains(text(), "est pas disponible")]')(self.doc)

    @method
    class iter_investment(ListElement):
        item_xpath = '(//div[contains(@class, "m-table")])[1]//table/tbody/tr[not(contains(@class, "total"))]'

        class item(ItemElement):
            klass = Investment

            def condition(self):
                return Field('label')(self) not in ('Total', '')

            obj_quantity = CleanDecimal.French('./td[contains(@data-label, "Nombre de parts")]', default=NotAvailable)
            obj_unitvalue = CleanDecimal.French('./td[contains(@data-label, "Valeur de la part")]', default=NotAvailable)

            def obj_valuation(self):
                # Handle discrepancies between aviva & afer (Coalesce does not work here)
                if CleanText('./td[contains(@data-label, "Valeur de rachat")]')(self):
                    return CleanDecimal.French('./td[contains(@data-label, "Valeur de rachat")]')(self)
                return CleanDecimal.French(CleanText('./td[contains(@data-label, "Montant")]', children=False))(self)

            obj_vdate = Date(
                CleanText('./td[@data-label="Date de valeur"]'), dayfirst=True, default=NotAvailable
            )

            obj_label = Coalesce(
                CleanText('./th[@data-label="Nom du support"]/a'),
                CleanText('./th[@data-label="Nom du support"]'),
                CleanText('./td[@data-label="Nom du support"]'),
            )

            obj_code = IsinCode(
                Regexp(
                    CleanText('./td[@data-label="Nom du support"]/a/@onclick|./th[@data-label="Nom du support"]/a/@onclick'),
                    r'"(.*)"',
                    default=NotAvailable
                ),
                default=NotAvailable
            )
            obj_code_type = IsinType(Field('code'))


class TransactionElement(ItemElement):
    klass = Transaction

    obj_label = Format('%s du %s', Field('_labeltype'), Field('date'))
    obj_date = Date(
        Regexp(
            CleanText(
                './ancestor::div[@class="onerow" or starts-with(@id, "term") or has-class("grid")]/'
                'preceding-sibling::h3[1]//div[contains(text(), "Date")]'
            ),
            r'(\d{2}\/\d{2}\/\d{4})'),
        dayfirst=True
    )
    obj_type = Transaction.TYPE_BANK

    obj_amount = CleanDecimal.French(
        './ancestor::div[@class="onerow" or starts-with(@id, "term") or has-class("grid")]/'
        'preceding-sibling::h3[1]//div[has-class("montant-mobile")]',
        default=NotAvailable
    )

    obj__labeltype = Regexp(
        Title('./preceding::h2[@class="feature"][1]'),
        r'Historique Des\s+(\w+)'
    )

    def obj_investments(self):
        return list(self.iter_investments(self.page, parent=self))

    @method
    class iter_investments(ListElement):
        item_xpath = './div[@class="line"]'

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText('./div[@data-label="Nom du support" or @data-label="Support cible"]/span[1]')
            obj_quantity = CleanDecimal.French('./div[contains(@data-label, "Nombre")]', default=NotAvailable)
            obj_unitvalue = CleanDecimal.French('./div[contains(@data-label, "Valeur")]', default=NotAvailable)
            obj_valuation = CleanDecimal.French('./div[contains(@data-label, "Montant")]', default=NotAvailable)
            obj_vdate = Env('date')

    def parse(self, el):
        self.env['date'] = Field('date')(self)


class HistoryPage(LoggedPage, HTMLPage):
    @method
    class iter_versements(ListElement):
        item_xpath = '//div[contains(@id, "versementProgramme3") or contains(@id, "versementLibre3")]/h2'

        class item(ItemElement):
            klass = Transaction
            obj_date = Date(
                Regexp(CleanText('./div[1]'), r'(\d{2}\/\d{2}\/\d{4})'),
                dayfirst=True
            )
            obj_amount = Eval(lambda x: x / 100, CleanDecimal('./div[2]'))
            obj_label = Format(
                '%s %s',
                CleanText('./preceding::h3[1]'),
                Regexp(CleanText('./div[1]'), r'(\d{2}\/\d{2}\/\d{4})')
            )

            def obj_investments(self):
                investments = []

                for elem in self.xpath('./following-sibling::div[1]//ul'):
                    inv = Investment()
                    inv.label = CleanText('./li[1]/p')(elem)
                    inv.portfolio_share = CleanDecimal('./li[2]/p', replace_dots=True, default=NotAvailable)(elem)
                    inv.quantity = CleanDecimal('./li[3]/p', replace_dots=True, default=NotAvailable)(elem)
                    inv.valuation = CleanDecimal('./li[4]/p', replace_dots=True)(elem)
                    investments.append(inv)

                return investments

    @method
    class iter_arbitrages(ListElement):
        item_xpath = '//div[contains(@id, "arbitrageLibre3")]/h2'

        class item(ItemElement):
            klass = Transaction
            obj_date = Date(
                Regexp(CleanText('.//div[1]'), r'(\d{2}\/\d{2}\/\d{4})'),
                dayfirst=True
            )
            obj_label = Format(
                '%s %s',
                CleanText('./preceding::h3[1]'),
                Regexp(CleanText('./div[1]'), r'(\d{2}\/\d{2}\/\d{4})')
            )

            def obj_amount(self):
                return sum(x.valuation for x in Field('investments')(self))

            def obj_investments(self):
                investments = []
                for elem in self.xpath('./following-sibling::div[1]//tbody/tr'):
                    inv = Investment()
                    inv.label = CleanText('./td[1]')(elem)
                    inv.valuation = Coalesce(
                        CleanDecimal.French('./td[2]/p', default=NotAvailable),
                        CleanDecimal.French('./td[2]')
                    )(elem)
                    investments.append(inv)

                return investments


class ActionNeededPage(LoggedPage, HTMLPage):
    def on_load(self):
        raise ActionNeeded('Veuillez mettre à jour vos coordonnées')


class ValidationPage(LoggedPage, HTMLPage):
    def on_load(self):
        error_message = CleanText('//p[@id="errorSigned"]')(self.doc)
        if error_message:
            raise ActionNeeded(error_message)


class InvestDetailPage(LoggedPage, HTMLPage):
    pass


class InvestPerformancePage(LoggedPage, HTMLPage):
    @method
    class fill_investment(ItemElement):
        obj_unitprice = CleanDecimal.US('//span[contains(@data-module-target, "BuyValue")]')
        obj_description = CleanText('//td[contains(text(), "Nature")]/following-sibling::td')
        obj_diff_ratio = Eval(
            lambda x: x / 100 if x else NotAvailable,
            CleanDecimal.US('//span[contains(@data-module-target, "trhrthrth")]', default=NotAvailable)
        )
