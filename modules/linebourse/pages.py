# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent Ardisson
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

from __future__ import unicode_literals

import re

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.elements import method, TableElement, ItemElement
from weboob.browser.filters.standard import (
    CleanText, Date, CleanDecimal, Regexp, Eval, Field
)
from weboob.browser.filters.html import TableCell
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.bank import Investment
from weboob.tools.capabilities.bank.transactions import FrenchTransaction as Transaction
from weboob.exceptions import ActionNeeded


def MyDecimal(*args, **kwargs):
    kwargs['replace_dots'] = True
    return CleanDecimal(*args, **kwargs)


class MainPage(LoggedPage, HTMLPage):
    pass


class FirstConnectionPage(LoggedPage, HTMLPage):
    def on_load(self):
        raise ActionNeeded(CleanText('//p[contains(text(), "prendre connaissance")]')(self.doc))


class AccountPage(LoggedPage, HTMLPage):
    def is_on_right_portfolio(self, account_id):
        return len(self.doc.xpath('//form[@class="choixCompte"]//option[@selected and contains(text(), $id)]', id=account_id))

    def get_compte(self, account_id):
        values = self.doc.xpath('//option[contains(text(), $id)]/@value', id=account_id)
        assert len(values) == 1, 'could not find account %r' % account_id
        if re.search(r'[0-9]\+', values[0]):
            # When the last character of the left is numeric we add the Hex value of "+" (requests specificity)
            values = [values[0].replace("+", "%2B")]

        return values[0]


class HistoryPage(AccountPage):
    def get_periods(self):
        return list(self.doc.xpath('//select[@id="ListeDate"]/option/@value'))

    @method
    class iter_history(TableElement):
        col_date = 'Date'
        col_name = 'Valeur'
        col_quantity = u'Quantité'
        col_amount = u'Montant net EUR'
        col_label = u'Opération'

        head_xpath = u'//table[@summary="Historique operations"]//tr[th]/th'
        item_xpath = u'//table[@summary="Historique operations"]//tr[not(th)]'

        def parse(self, el):
            self.labels = {}

        class item(ItemElement):
            def condition(self):
                text = CleanText('td')(self)
                return not text.startswith('Aucune information disponible')

            klass = Transaction

            obj_date = Date(CleanText(TableCell('date')), dayfirst=True)
            obj_amount = MyDecimal(TableCell('amount'))
            obj_raw = CleanText(TableCell('label'))

            def obj_investments(self):
                inv = Investment()
                inv.quantity = CleanDecimal(TableCell('quantity'), replace_dots=True)(self)
                inv.code_type = Investment.CODE_TYPE_ISIN

                txt = CleanText(TableCell('name'))(self)
                match = re.match('(?:(.*) )?- ([^-]+)$', txt)
                inv.label = match.group(1) or NotAvailable
                inv.code = match.group(2)

                if inv.code in self.parent.labels:
                    inv.label = inv.label or self.parent.labels[inv.code]
                elif inv.label:
                    self.parent.labels[inv.code] = inv.label
                else:
                    inv.label = inv.code

                return [inv]


class InvestmentPage(AccountPage):
    @method
    class get_investment(TableElement):
        col_label = 'Valeur'
        col_quantity = u'Quantité'
        col_valuation = u'Valorisation EUR'
        col_unitvalue = 'Cours/VL'
        col_unitprice = 'Prix moyen EUR'
        col_portfolio_share = '% Actif'
        col_diff = u'+/- value latente EUR'

        head_xpath = u'//table[starts-with(@summary,"Contenu du portefeuille")]/thead//th'
        item_xpath = u'//table[starts-with(@summary,"Contenu du portefeuille")]/tbody/tr[2]'

        class item(ItemElement):
            klass = Investment

            def condition(self):
                return Field('quantity')(self) != NotAvailable and Field('quantity')(self) > 0

            obj_quantity = MyDecimal(TableCell('quantity'), default=NotAvailable)
            obj_unitvalue = MyDecimal(TableCell('unitvalue'), default=NotAvailable)
            obj_unitprice = MyDecimal(TableCell('unitprice'), default=NotAvailable)
            obj_valuation = MyDecimal(TableCell('valuation'))
            obj_portfolio_share = Eval(lambda x: x / 100 if x else NotAvailable, MyDecimal(TableCell('portfolio_share'), default=NotAvailable))
            obj_diff = MyDecimal(TableCell('diff', default=NotAvailable), default=NotAvailable)
            obj_code_type = Investment.CODE_TYPE_ISIN

            obj_label = CleanText(Regexp(CleanText('./preceding-sibling::tr/td[1]'), '(.*)- .*'))
            obj_code = Regexp(CleanText('./preceding-sibling::tr/td[1]'), '- (.*)')

    def iter_investment(self):
        valuation = MyDecimal('//td[@class="donneeNumerique borderbottom "]/text()')(self.doc)
        if valuation is not None:
            inv = Investment()
            inv.code = 'XX-liquidity'
            inv.code_type = NotAvailable
            inv.label = 'Liquidités'
            inv.valuation = valuation
            yield inv
        for inv in self.get_investment():
            yield inv


class MessagePage(LoggedPage, HTMLPage):
    def submit(self):
        # taken from linebourse implementation in caissedepargne module
        form = self.get_form(name='leForm')
        form['signatur1'] = 'on'
        form.submit()


class BrokenPage(LoggedPage, HTMLPage):
    pass
