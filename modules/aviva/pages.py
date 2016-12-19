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


from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import CleanText, Capitalize, Format, Date, Regexp, CleanDecimal, Env, Field, Async, AsyncLoad
from weboob.browser.filters.html import Attr, Link
from weboob.capabilities.bank import Account, Investment, Transaction
from weboob.capabilities.base import NotAvailable


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)


class LoginPage(HTMLPage):
    def get_values(self):
        values = {}
        for input in self.doc.xpath('//input[@keypad]'):
            value = Attr(None, 'value').filter(input.xpath('.'))
            index = Attr(None, 'data-index').filter(input.xpath('.'))
            values[value] = index
        return values

    def get_password(self, password):
        values = self.get_values()
        password = [values[c] for c in password]
        return "".join(password)

    def login(self, login, password):
        form = self.get_form(id="loginForm")
        form['username'] = login
        form['password'] = self.get_password(password)
        form.submit()


class AccountsPage(LoggedPage, HTMLPage):
    @method
    class iter_accounts(ListElement):
        item_xpath = '//div[@id]/div[has-class("productDetails")]'

        class item(ItemElement):
            klass = Account

            load_details = Field('_link') & AsyncLoad

            obj_id = CleanText('.//dt[contains(text(), "contrat")]/following-sibling::dd[1]')
            obj_label = CleanText('.//div[has-class("title")]')
            obj_type = Account.TYPE_LIFE_INSURANCE
            obj_balance = Async('details') & MyDecimal('.//strong[contains(text(), "Valeur")]/following-sibling::span')
            obj_valuation_diff = Async('details') & MyDecimal('.//a[contains(@title, "diff")]/parent::p')
            obj__link = Link(u'.//a[contains(text(), "Détail")]')
            # Additional waranty : need to know what to do with this
            obj__additionalwaranty = Env('additionalwaranty')

            def condition(self):
                return 'epargne' in Link(u'.//a[contains(text(), "Détail")]')(self)

            def parse(self, el):
                # Additional waranty
                doc = self.page.browser.open(Field('_link')(self)).page.doc
                additionalwaranty = []
                for line in doc.xpath(u'//h2[contains(text(), "complémentaire")]/following-sibling::div//div[@class="line"]'):
                    values = {}
                    values['label'] = CleanText().filter(line.xpath('./div[@data-label="Nom du support"]'))
                    values['amount'] = CleanText().filter(line.xpath('./div[@data-label="Montant total investi"]'))
                    additionalwaranty.append(values)
                self.env['additionalwaranty'] = additionalwaranty


class InvestmentPage(LoggedPage, HTMLPage):
    def get_history_link(self):
        return self.doc.xpath(u'//a[contains(text(), "historique")]/@href')[0]

    @method
    class iter_investment(ListElement):
        item_xpath = '//h2[has-class("feature")]/following-sibling::div/div[@class="line"]'

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText('./div[@data-label="Nom du support"]/text()')
            obj_code = Regexp(Attr('./div[@data-label="Nom du support"]/a', 'onclick', default=''), '\"([^\"]+)', default=NotAvailable)
            obj_quantity = MyDecimal('./div[@data-label="Nombre de parts"]', default=NotAvailable)
            obj_unitvalue = MyDecimal('./div[@data-label="Valeur de la part"]')
            obj_valuation = MyDecimal('./div[@data-label="Valeur"]', default=NotAvailable)
            obj_vdate = Date(CleanText('./div[@data-label="Date de valeur"]'), dayfirst=True, default=NotAvailable)


class HistoryPage(LoggedPage, HTMLPage):
    @method
    class iter_history(ListElement):
        item_xpath = '//div[@class="table-responsive"]'

        class item(ItemElement):
            klass = Transaction

            obj_label = Format('%s du %s', Env('label'), Field('date'))
            obj_date = Date(Regexp(CleanText('./ancestor::div[contains(@id, "term") or has-class("grid")]/ \
                            preceding-sibling::h3//div[contains(text(), "Date")]'), ':[\s]+([\d\/]+)'), dayfirst=True)
            obj_type = Transaction.TYPE_BANK
            obj_amount = MyDecimal(Env('amount'))
            obj_investments = Env('investments')

            def parse(self, el):
                label = Regexp(Capitalize('./ancestor::div[@class="bloc-accordeon"]/ \
                            preceding-sibling::h2[1]'), 'Des[\s]+([\w]+)')(self)
                self.env['label'] = label[:-1]
                amount = CleanText('./ancestor::div[contains(@id, "term")]/ \
                            preceding-sibling::h3//div[contains(@class, "montant")]')(self)
                if not amount:
                    amount = CleanText('.//div[@class="line"]/div[contains(@data-label, "Montant")]')(self)
                self.env['amount'] = amount

                investments = []
                for line in el.xpath('./div[@class="line"]'):
                    i = Investment()
                    i.label = CleanText().filter(line.xpath('./div[@data-label="Nom du support" or @data-label="Support cible"]/span[1]'))
                    i.quantity = MyDecimal().filter(line.xpath('./div[contains(@data-label, "Nombre")]'))
                    i.unitvalue = MyDecimal().filter(line.xpath('./div[contains(@data-label, "Valeur")]'))
                    i.valuation = MyDecimal().filter(line.xpath('./div[contains(@data-label, "Montant")]'))
                    i.vdate = Field('date')(self)
                    investments.append(i)

                self.env['investments'] = investments
