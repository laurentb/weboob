# -*- coding: utf-8 -*-

# Copyright(C) 2019 Sylvie Ye
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import re

from weboob.browser.pages import LoggedPage, JsonPage
from weboob.browser.elements import method, DictElement, ItemElement
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import (
    CleanText, CleanDecimal, Date, Eval, Lower, Format, Field, Map, Upper,
)
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.capabilities.base import NotAvailable


class Transaction(FrenchTransaction):
    PATTERNS = [
        (re.compile(u'^retrait dab (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{4}) (?P<text>.*)'), FrenchTransaction.TYPE_WITHDRAWAL),
        # Withdrawal in foreign currencies will look like "retrait 123 currency"
        (re.compile(u'^retrait (?P<text>.*)'), FrenchTransaction.TYPE_WITHDRAWAL),
        (re.compile(u'^carte (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{4}) (?P<text>.*)'), FrenchTransaction.TYPE_CARD),
        (re.compile(u'^virement (sepa )?(emis vers|recu|emis)? (?P<text>.*)'), FrenchTransaction.TYPE_TRANSFER),
        (re.compile(u'^remise cheque(?P<text>.*)'), FrenchTransaction.TYPE_DEPOSIT),
        (re.compile(u'^cheque (?P<text>.*)'), FrenchTransaction.TYPE_CHECK),
        (re.compile(u'^prelevement (?P<text>.*)'), FrenchTransaction.TYPE_ORDER),
        (re.compile(u'^prlv sepa (?P<text>.*?) : .*'), FrenchTransaction.TYPE_ORDER),
        (re.compile(u'^prélèvement sepa en faveur de (?P<text>.*)'), FrenchTransaction.TYPE_ORDER),
        (re.compile(u'^commission sur (?P<text>.*)'), FrenchTransaction.TYPE_BANK),
    ]

    TYPES = {
        'PURCHASE_CARD': FrenchTransaction.TYPE_CARD,
        'TRANSFER': FrenchTransaction.TYPE_TRANSFER,
        'SEPA_DEBIT': FrenchTransaction.TYPE_ORDER,
        'CARD_WITHDRAWAL': FrenchTransaction.TYPE_WITHDRAWAL,
        'FEES': FrenchTransaction.TYPE_BANK,
        'CHECK': FrenchTransaction.TYPE_CHECK,
        'OTHER': FrenchTransaction.TYPE_UNKNOWN,
    }


class AccountsPage(LoggedPage, JsonPage):
    @method
    class iter_accounts(DictElement):
        item_xpath = 'accounts'

        class item(ItemElement):
            klass = Account

            obj_id = Dict('uid')
            obj_label = Dict('type/label')
            obj_number = CleanText(Dict('label'), replace=[(' ', '')])

            def obj_balance(self):
                if not Dict('hasPositiveBalance')(self):
                    return -CleanDecimal(Dict('ledgerBalance'))(self)
                return CleanDecimal(Dict('ledgerBalance'))(self)


class HistoryPage(LoggedPage, JsonPage):
    def is_empty_page(self):
        return len(self.doc) == 0

    @method
    class iter_history(DictElement):
        class item(ItemElement):
            klass = Transaction

            # Not sure that Dict('id') is unique and persist
            # wait for the full API migration
            obj__web_id = Eval(str, Dict('id'))
            obj_amount = CleanDecimal(Dict('amount'))
            obj_date = Date(Dict('effectiveDate'))
            obj_type = Map(Upper(Dict('type')), Transaction.TYPES, Transaction.TYPE_UNKNOWN)

            def obj_raw(self):
                return Transaction.Raw(Lower(Dict('detail')))(self) or Format('%s %s', Field('date'), Field('amount'))(self)


class ComingPage(LoggedPage, JsonPage):
    @method
    class iter_coming(DictElement):
        item_xpath = 'futureOperations'

        class item(ItemElement):
            klass = Transaction

            obj_amount = CleanDecimal(Dict('amount'))
            obj_date = Date(Dict('effectiveDate'))
            obj_vdate = Date(Dict('operationDate'))
            obj_type = Map(Upper(Dict('type')), Transaction.TYPES, Transaction.TYPE_UNKNOWN)

            def obj_raw(self):
                return Transaction.Raw(Lower(Dict('label')))(self) or Format('%s %s', Field('date'), Field('amount'))(self)

    @method
    class get_account_coming(ItemElement):
        klass = Account

        obj_coming = CleanDecimal(Dict('totalAmount', default=NotAvailable), default=NotAvailable)
