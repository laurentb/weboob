# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
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

from decimal import Decimal
from datetime import date
import re

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.elements import TableElement, ItemElement, method
from weboob.browser.filters.standard import CleanText, CleanDecimal, Date, Env, Regexp, Field
from weboob.browser.filters.html import TableCell
from weboob.capabilities.bank import Account, Transaction, Investment, Pocket
from weboob.capabilities.base import NotAvailable


class LoginPage(HTMLPage):
    def login(self, login, passwd):
        form = self.get_form(nr=0)
        form['_cm_user'] = login
        form['_cm_pwd'] = passwd
        form.submit()


class LoginErrorPage(HTMLPage):
    pass


class GroupamaesPage(LoggedPage, HTMLPage):
    NEGATIVE_AMOUNT_LABELS = [u'Retrait', u'Transfert sortant', u'Frais']

    @method
    class iter_accounts(TableElement):
        item_xpath = u'//table[@summary="Liste des échéances"]/tbody/tr'
        head_xpath = u'//table[@summary="Liste des échéances"]/thead/tr/th/text()'

        col_name = u'Plan'
        col_value = u'Evaluation en'

        class item(ItemElement):
            klass = Account

            def condition(self):
                return u'Vous n\'avez pas d\'avoirs.' not in CleanText(TableCell('name'))(self)

            obj_id = CleanText(TableCell('name'))
            obj_label = CleanText(TableCell('name'))
            obj_balance = CleanDecimal(TableCell('value'), replace_dots=True, default=Decimal(0))
            obj_currency = CleanText(u'//table[@summary="Liste des échéances"]/thead/tr/th/small/text()')
            obj_type = Account.TYPE_PEE

    def iter_investment(self):
        item = self.doc.xpath(u'//table[@summary="Liste des échéances"]/tfoot/tr/td[@class="tot _c1 d _c1"]')[0]
        total = CleanDecimal(Regexp(CleanText('.'), '(.*) .*'),
                             default=1, replace_dots=True)(item)

        item_xpath = u'((//table[@summary="Liste des échéances"])[1]/tbody/tr)[position() < last() and not(contains(./td[1]/@class, "tittot"))]'

        obj = None
        for tr in self.doc.xpath(item_xpath):
            tds = tr.xpath('./td')
            if len(tds) > 3:
                if obj is not None:
                    obj.portfolio_share = (obj.valuation / total).quantize(Decimal('.0001'))
                    yield obj

                obj = Investment()
                obj.label = CleanText('.')(tds[0])
                obj.vdate = date.today()  # * En réalité derniere date de valorisation connue
                obj.unitvalue = CleanDecimal('.', replace_dots=True)(tds[2])
                obj.valuation = CleanDecimal('.', replace_dots=True)(tds[5])
                obj.quantity = CleanDecimal('.', replace_dots=True)(tds[4])

            elif obj is not None:
                obj.quantity += CleanDecimal('.', replace_dots=True)(tds[1])
                obj.valuation += CleanDecimal('.', replace_dots=True)(tds[2])

        if obj is not None:
            obj.portfolio_share = (obj.valuation / total).quantize(Decimal('.0001'))
            yield obj

    @method
    class get_history(TableElement):
        head_xpath = u'(//table[@summary="Liste des opérations"])[1]/thead/tr/th/text()'
        item_xpath = u'(//table[@summary="Liste des opérations"])[1]/tbody/tr'

        col_date = u'Date'
        col_operation = u'Opération'
        col_montant = [u'Montant net en EUR', 'Montant en']

        class item(ItemElement):
            klass = Transaction

            def condition(self):
                return u'Aucune opération' not in CleanText(TableCell('date'))(self)

            obj_date = Date(CleanText(TableCell('date')), Env('date_guesser'))
            obj_type = Transaction.TYPE_UNKNOWN
            obj_label = CleanText(TableCell('operation'))

            def obj_amount(self):
                amount = CleanDecimal(TableCell('montant'), replace_dots=True, default=NotAvailable)(self)
                if amount is NotAvailable:
                    assert self.env.get('coming')
                    return amount

                for pattern in GroupamaesPage.NEGATIVE_AMOUNT_LABELS:
                    if Field('label')(self).startswith(pattern):
                        amount = -amount
                return amount

    @method
    class get_list(TableElement):
        head_xpath = u'//table[@summary="Liste des opérations en attente"]/thead/tr/th/text()'
        item_xpath = u'//table[@summary="Liste des opérations en attente"]/tbody/tr'

        col_date = u'Date'
        col_operation = u'Opération'
        col_etat = u'Etat'
        col_montant = [u'Montant net en', re.compile(u'Montant en')]
        col_action = u'Action'

        class item(ItemElement):
            klass = Transaction

            def condition(self):
                return u'Aucune opération en attente' not in CleanText(TableCell('date'))(self)

            obj_date = Date(CleanText(TableCell('date')), Env('date_guesser'))
            obj_type = Transaction.TYPE_UNKNOWN
            obj_label = CleanText(TableCell('operation'))
            obj_amount = CleanDecimal(TableCell('montant'), replace_dots=True)


class GroupamaesPocketPage(LoggedPage, HTMLPage):
    CONDITIONS = {u'immédiate': Pocket.CONDITION_AVAILABLE,
                  u'à':   Pocket.CONDITION_RETIREMENT,
                 }

    def iter_investment(self, label):
        for tr in self.doc.xpath(u'//table[@summary="Liste des échéances"]/tbody/tr'):
            tds = tr.findall('td')

            inv = Investment()
            i = 1

            if len(tds) <= 2:
                continue

            inv.label = CleanText(tds[i])(tr)
            inv.quantity = CleanDecimal(tds[i+3], replace_dots=True)(tr)
            inv.valuation = CleanDecimal(tds[i+4], replace_dots=True)(tr)

            if 'PEI' in label.split()[0]:
                label = 'PEE'
            if Regexp(CleanText(tds[i]), '\(([\w]+).*\)$')(tr) not in label.split()[0]:
                continue

            yield inv

    def iter_pocket(self, label):
        date_available, condition = 0, 0
        for tr in self.doc.xpath(u'//table[@summary="Liste des échéances"]/tbody/tr'):
            tds = tr.findall('td')

            pocket = Pocket()
            i = 0

            if len(tds) <= 2 :
                continue
            elif len(tds) < 6:
                pocket.availability_date = date_available
                pocket.condition = condition
            else:
                i+=1
                pocket.availability_date = Date(Regexp(CleanText(tds[0]), '([\d\/]+)', default=NotAvailable), default=NotAvailable)(tr)
                date_available = pocket.availability_date

                pocket.condition = Pocket.CONDITION_DATE if pocket.availability_date is not NotAvailable else \
                                            self.CONDITIONS.get(CleanText(tds[0])(tr).lower().split()[0], Pocket.CONDITION_UNKNOWN)
                condition = pocket.condition

            pocket.label = CleanText(tds[i])(tr)
            pocket.quantity = CleanDecimal(tds[i+3], replace_dots=True)(tr)
            pocket.amount = CleanDecimal(tds[i+4], replace_dots=True)(tr)

            if 'PEI' in label.split()[0]:
                label = 'PEE'
            if Regexp(CleanText(tds[i]), '\(([\w]+).*\)$')(tr) not in label.split()[0]:
                continue

            yield pocket
