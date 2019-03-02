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

from weboob.browser.pages import HTMLPage, LoggedPage, pagination
from weboob.browser.elements import ListElement, ItemElement, method, TableElement
from weboob.browser.filters.standard import (
    CleanText, Upper, Date, Regexp, Field,
    CleanDecimal, Env, Async, AsyncLoad, Currency,
    )
from weboob.browser.filters.html import Link, TableCell, Attr
from weboob.capabilities.bank import Account, Investment, Pocket
from weboob.capabilities.base import NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.exceptions import ActionNeeded


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)


class LoginPage(HTMLPage):
    def login(self, login, password):
        form = self.get_form(name="bloc_ident")
        form['_cm_user'] = login
        form['_cm_pwd'] = password
        form.submit()


class AccountsPage(LoggedPage, HTMLPage):
    def on_load(self):
        if self.doc.xpath('//label[contains(@for, "AcceptCGU")]'):
            raise ActionNeeded(CleanText('//table[contains(@summary, "Conditions g")]')(self.doc))

    def get_investment_link(self):
        return Link('//a[contains(text(), "Par fonds") or contains(@href,"GoPositionsParFond")]', default=None)(self.doc)

    def get_pocket_link(self):
        return Link('//a[contains(@href, "CCB")]', default=None)(self.doc)

    @method
    class iter_accounts(ListElement):
        class item(ItemElement):
            klass = Account

            obj_id = Regexp(Upper(Field('label')), '[\s]+([^\s]+)[\s]+([^\s]+).*:[\s]+([^\s]+)', '\\1\\2\\3')
            obj_type = Account.TYPE_PEE
            obj_label = CleanText('(//table[@class="fiche"]//td)[1]')

            def obj_balance(self):
                if CleanText('//td[text()="Vous n\'avez pas d\'avoirs."]')(self):
                    return 0

                balance = MyDecimal('//table[@class="fiche"]//td/em')(self)
                if not balance:
                    balance = MyDecimal('//th[contains(text(), "Montant total")]/em')(self)
                return balance

            def obj_currency(self):
                currency = CleanText('//th[contains(text(), "Montant total")]/small')(self)
                if currency:
                    return Currency().filter(currency)
                return Currency().filter(CleanText('//table[@class="fiche"]//td/small')(self))


class FCPEInvestmentPage(LoggedPage, HTMLPage):
    @method
    class iter_investment(TableElement):
        item_xpath = '//tbody/tr'
        head_xpath = '//table/thead/tr/th'

        # forced to write the currency
        col_label = 'Fonds'
        col_quantity = 'Nombre de parts'
        col_unitprice = re.compile('Net investi en EUR')
        col_diff = re.compile('Valeur liquidative \(VL\) en EUR')
        col_valuation = re.compile('Evaluation en EUR')
        col_diff_percent = re.compile('\+\/- values latentes')

        def condition(self):
            return not CleanText('//td[text()="Vous n\'avez pas d\'avoirs."]')(self)

        class item(ItemElement):
            klass = Investment

            # array starts at 1
            # can not use TableCell here because there is 2 sub columns
            obj__pocket_url = Link('./td[1]/a')
            obj_label = CleanText('./td[2]')
            obj_quantity = MyDecimal(TableCell('quantity'))
            # displays only with table format
            obj_unitprice = MyDecimal(TableCell('unitprice'))
            obj_diff = MyDecimal(TableCell('diff'))
            # take only the plain text
            obj_valuation = MyDecimal('./td[7]/text()')
            obj_diff_percent = MyDecimal(TableCell('diff_percent'))
            # good vdate?
            obj_vdate = Date(Regexp(CleanText(u'//p[contains(text(), "financière au ")]'), 'au[\s]+(.*)'), dayfirst=True)

    @method
    class iter_pocket(ListElement):
        # Getting the only tr which is unfolded
        item_xpath = '//table[@class="liste"]/tbody/tr[td/a/img[@alt="[-] Détail"]]/following::tr[not(td/a/img[@alt="[+] Détail"])]'

        class item(ItemElement):
            klass = Pocket

            obj_investment = Env('inv')
            obj_label = CleanText('//table[@class="liste"]/tbody/tr[td/a/img[@alt="[-] Détail"]]/td[2]')
            obj_amount = MyDecimal('./td[4]')
            obj_quantity = MyDecimal('./td[3]')

            def obj_availability_date(self):
                return Date(CleanText('./td[2]'), dayfirst=True, default=NotAvailable)(self)


class CCBInvestmentPage(LoggedPage, HTMLPage):
    def iter_investment(self):
        el_list = self.doc.xpath('//table[@class="liste"]/tbody/tr')

        for index, el in enumerate(el_list):
            try:
                rowspan = int(Attr(el.xpath('./td[has-class("g")]'), 'rowspan')(self))
            except:
                continue

            inv = Investment()
            inv.label = CleanText(el.xpath('./td[has-class("i g")]'))(self.doc)
            inv.valuation = MyDecimal(el.xpath('./td[last()]'))(self.doc)
            inv._pocket_url = None
            for i in range(1, rowspan):
                # valuation is not directly written on website, but it's separated by pocket, so we compute it here,
                # and is also written in footer so it's sum of all valuation, not just one
                inv.valuation += MyDecimal(el_list[index+i].xpath('./td[last()]'))(self.doc)

            yield inv

    @method
    class iter_pocket(ListElement):
        item_xpath = '//table[@class="liste"]/tbody/tr'

        class item(ItemElement):
            klass = Pocket

            def parse(self, obj):
                label = CleanText('./td[has-class("g")]')(self)
                if not label:
                    label = CleanText('./preceding-sibling::tr/td[has-class("g")]')(self)
                    availability_date = Date(Regexp(CleanText('./td[1]'), 'au[\s]+(.*)'), dayfirst=True)(self)
                else:
                    availability_date = Date(Regexp(CleanText('./td[2]'), 'au[\s]+(.*)'), dayfirst=True)(self)

                self.env['label'] = label
                self.env['availability_date'] = availability_date

            obj_label = Env('label')
            obj_amount = MyDecimal('./td[last()]')
            obj_availability_date = Env('availability_date')
            obj_condition = Pocket.CONDITION_DATE
            obj_investment = Env('inv')


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(u'^(?P<text>Versement.*)'),  FrenchTransaction.TYPE_DEPOSIT),
                (re.compile(u'^(?P<text>(Arbitrage|Prélèvements.*))'), FrenchTransaction.TYPE_ORDER),
                (re.compile(u'^(?P<text>Retrait.*)'), FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(u'^(?P<text>.*)'), FrenchTransaction.TYPE_BANK),
               ]


class HistoryPage(LoggedPage, HTMLPage):
    DEBIT_WORDS = ['sortant', 'paiement', 'retrait', 'frais']

    def get_link(self):
        return Link(u'//a[contains(text(), "Vos opérations traitées")]', default=None)(self.doc)

    @method
    class get_investments(TableElement):
        item_xpath = '//table/tbody/tr'
        head_xpath = '//table/thead/tr/th'

        col_label = u'Support'
        col_unitvalue = re.compile(u'Valeur')
        col_quantity = u'Nombre de parts'
        col_valuation = [re.compile(u'Transfert demandé'), re.compile(u'Versement souhaité'), \
                         re.compile(u'Arbitrage demandé'), re.compile(u'Paiement demandé'), \
                         re.compile(u'Montant net')]

        class item(ItemElement):
            klass = Investment

            condition = lambda self: len(self.el.xpath('./td')) == 9

            obj_label = CleanText(TableCell('label'))
            obj_quantity = CleanDecimal(TableCell('quantity'), default=NotAvailable)
            obj_unitvalue = CleanDecimal(TableCell('unitvalue'), default=NotAvailable)
            obj_valuation = CleanDecimal(TableCell('valuation'), default=NotAvailable)

            def obj_vdate(self):
                return Date(Regexp(CleanText(u'//p[contains(text(), " du ")]'), 'du ([\d\/]+)'), dayfirst=True)(self)

    @pagination
    @method
    class iter_history(TableElement):
        item_xpath = u'//table[@summary="Liste des opérations"]/tbody/tr'
        head_xpath = u'//table[@summary="Liste des opérations"]/thead/tr/th'

        col_date = u'Date'
        col_label = u'Opération'
        col_amount = re.compile(u'Montant')

        next_page = Link('//a[contains(@href, "Suiv")]', default=None)

        def condition(self):
            return not CleanText('//td[contains(@class, "vide") and contains(text(), "Aucune op")]')(self)

        class item(ItemElement):
            klass = Transaction

            load_details = Link('.//a[1]', default=None) & AsyncLoad

            obj_date = Date(CleanText(TableCell('date')), dayfirst=True)
            obj_raw = Transaction.Raw(Env('label'))
            obj_amount = Env('amount')
            obj_investments = Env('investments')

            def parse(self, el):
                page = Async('details').loaded_page(self)
                label = CleanText(TableCell('label')(self)[0].xpath('./a[1]'))(self)

                # Try to get gross amount
                amount = None
                for td in page.doc.xpath('//td[em[1][contains(text(), "Total")]]/following-sibling::td'):
                    amount = CleanDecimal('.', default=None)(td)
                    if amount:
                        break

                amount = amount or MyDecimal(TableCell('amount'))(self)
                if any(word in label.lower() for word in self.page.DEBIT_WORDS):
                    amount = -amount

                self.env['label'] = label
                self.env['amount'] = amount
                self.env['investments'] = list(page.get_investments())


class CustomPage(LoggedPage, HTMLPage):
    pass
