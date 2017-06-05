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
from weboob.exceptions import ActionNeeded, BrowserUnavailable


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)


class BasePage(HTMLPage):
    def on_load(self):
        super(BasePage, self).on_load()

        if 'Erreur' in CleanText('//div[@id="main"]/h1', default='')(self.doc):
            err = CleanText('//div[@id="main"]/div[@class="content"]', default=u'Site indisponible')(self.doc)
            raise BrowserUnavailable(err)


class LoginPage(BasePage, HTMLPage):
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


class AccountsPage(LoggedPage, BasePage, HTMLPage):
    @method
    class iter_accounts(ListElement):
        item_xpath = '//div[@id]/div[has-class("productDetails")]'

        class item(ItemElement):
            klass = Account

            load_details = Field('_link') & AsyncLoad

            obj_id = CleanText('.//dt[contains(text(), "contrat")]/following-sibling::dd[1]')
            obj_label = CleanText('.//div[has-class("title")]')
            obj_type = Account.TYPE_LIFE_INSURANCE
            obj_balance = Async('details') & MyDecimal('//strong[contains(text(), "Valeur") '
                'or contains(text(), "Epargne retraite")]/following-sibling::span')
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
        link = self.doc.xpath(u'//a[contains(text(), "historique")]/@href')
        if link:
            return link[0]

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


class InvestmentElement(ItemElement):
    klass = Investment

    obj_label = CleanText('./div[@data-label="Nom du support" or @data-label="Support cible"]/span[1]')
    obj_quantity = MyDecimal('./div[contains(@data-label, "Nombre")]')
    obj_unitvalue = MyDecimal('./div[contains(@data-label, "Valeur")]')
    obj_valuation = MyDecimal('./div[contains(@data-label, "Montant")]')
    obj_vdate = Env('date')
    #obj_vdate = Field('date')


class TransactionElement(ItemElement):
    klass = Transaction

    obj_label = Format('%s du %s', Field('_labeltype'), Field('date'))
    obj_date = Date(Regexp(CleanText('./ancestor::div[@class="onerow" or starts-with(@id, "term") or has-class("grid")]/'
                                     'preceding-sibling::h3[1]//div[contains(text(), "Date")]'),
                           r'(\d{2}\/\d{2}\/\d{4})'),
                    dayfirst=True)
    obj_type = Transaction.TYPE_BANK

    obj_amount = MyDecimal('./ancestor::div[@class="onerow" or starts-with(@id, "term") or has-class("grid")]/'
                           'preceding-sibling::h3[1]//div[has-class("montant-mobile")]', default=NotAvailable)

    obj__labeltype = Regexp(Capitalize('./preceding::h2[@class="feature"][1]'),
                                      'Historique Des\s+(\w+)')

    def obj_investments(self):
        return list(self.iter_investments(self.page, parent=self))

    @method
    class iter_investments(ListElement):
        item_xpath = './div[@class="line"]'

        class item(InvestmentElement):
            pass

    def parse(self, el):
        self.env['date'] = Field('date')(self)


class HistoryPage(LoggedPage, HTMLPage):
    @method
    class iter_history(ListElement):
        class iter_simple(ListElement):
            def find_elements(self):
                # "arbitrage" transactions are split in 2 table-responsive
                # the html tree is a mess
                for sub in self.el.xpath('//div[not(@id="divAvance")]/div[@class="table-responsive"]'):
                    if (sub.getparent().attrib.get('class') != 'onerow' or
                        'grid' not in sub.getparent().getparent().attrib.get('class')):

                        yield sub

            obj_date = Date(Regexp(CleanText('./ancestor::div[starts-with(@id, "term")/'
                                            'preceding-sibling::h3[1]//div[contains(text(), "Date")]'),
                                r'\d{2}\/\d{2}\/\d{4}'),
                            dayfirst=True)

            class item(TransactionElement):
                class iter_investments(ListElement):
                    item_xpath = './div[@class="line"]'

                    class item(InvestmentElement):
                        pass

        class iter_complex(ListElement):
            item_xpath = '//div[has-class("grid")]/div[@class="onerow"]'

            class item(TransactionElement):
                class iter_investments(ListElement):
                    item_xpath = './div[@class="table-responsive"]/div[@class="line"]'

                    class item(InvestmentElement):
                        pass

        class iter_avance(ListElement):
            item_xpath = '//div[@id="divAvance"]/div[@class="table-responsive"]/div[@class="line"]'

            class item(ItemElement):
                klass = Transaction

                obj_label = Format('%s du %s', Field('_labeltype'), Field('date'))
                obj_type = Transaction.TYPE_BANK
                obj_date = Date(CleanText(u'./div[@data-label="Date d\'effet"]', children=False), dayfirst=True)
                obj_amount = CleanDecimal(u'./div[@data-label="Montant en €"]', replace_dots=True)
                obj__labeltype = Regexp(Capitalize('./preceding::h2[@class="feature"][1]'),
                                        'Historique Des\s+(\w+)')


class ActionNeededPage(LoggedPage, HTMLPage):
    def on_load(self):
        raise ActionNeeded(u'Veuillez mettre à jour vos coordonnées')
