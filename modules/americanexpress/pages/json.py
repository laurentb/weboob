# -*- coding: utf-8 -*-

# Copyright(C) 2017 Vincent Ardisson
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

from ast import literal_eval
from decimal import Decimal
import re

from weboob.browser.pages import LoggedPage, JsonPage, HTMLPage
from weboob.browser.elements import ItemElement, DictElement, method
from weboob.browser.filters.standard import Date, Eval, CleanText, Field
from weboob.browser.filters.json import Dict
from weboob.capabilities.bank import Account, Transaction
from weboob.capabilities.base import NotAvailable
from weboob.tools.json import json
from .base import parse_decimal


def flatten(l):
    if not isinstance(l, list):
        yield l
        return

    for e in l:
        for s in flatten(e):
            yield s


def float_to_decimal(f):
    return Decimal(str(f))


class DashboardPage(LoggedPage, HTMLPage):
    pass


class AccountsPage3(LoggedPage, HTMLPage):
    def iter_accounts(self):
        for line in self.doc.xpath('//script[@id="initial-state"]')[0].text.split('\n'):
            m = re.search('window.__INITIAL_STATE__ = (.*);', line)
            if m:
                data = list(flatten(json.loads(literal_eval(m.group(1)))))
                break
        else:
            assert False, "data was not found"

        assert data.count('display_account_number') == 1, 'there should be exactly one card'

        acc = Account()
        acc.id = 'XXX-%s' % data[1 + data.index('display_account_number')]
        acc.label = '%s %s' % (data[1 + data.index('description')], data[1 + data.index('embossed_name')])
        acc._index = data[1 + data.index('sorted_index')]
        acc._token = data[1 + data.index('account_token')]
        yield acc


class JsonBalances(LoggedPage, JsonPage):
    def set_balances(self, accounts):
        by_token = {a._token: a for a in accounts}
        for d in self.doc:
            by_token[d['account_token']].coming = -float_to_decimal(d['total_debits_balance_amount'])
            by_token[d['account_token']].balance = -float_to_decimal(d['total_payments_credits_amount'])


class JsonBalances2(LoggedPage, JsonPage):
    def set_balances(self, accounts):
        by_token = {a._token: a for a in accounts}
        for d in self.doc:
            by_token[d['account_token']].balance = -float_to_decimal(d['total']['debits_total_amount'])
            # warning: payments_credits_total_amount is not the coming value here


class CurrencyPage(LoggedPage, JsonPage):
    def get_currency(self):
        return self.doc['currency']


class JsonPeriods(LoggedPage, JsonPage):
    def get_periods(self):
        return [p['statement_end_date'] for p in self.doc]


class JsonHistory(LoggedPage, JsonPage):
    def get_count(self):
        return self.doc['total_count']

    @method
    class iter_history(DictElement):
        item_xpath = 'transactions'

        class item(ItemElement):
            klass = Transaction

            def obj_type(self):
                if Field('raw')(self) in self.page.browser.SUMMARY_CARD_LABEL:
                    return Transaction.TYPE_CARD_SUMMARY
                elif Field('amount')(self) > 0:
                    return Transaction.TYPE_ORDER
                else:
                    return Transaction.TYPE_DEFERRED_CARD

            obj_raw = CleanText(Dict('description'))
            obj_date = Date(Dict('statement_end_date', default=None), default=None)
            obj_rdate = Date(Dict('charge_date'))
            obj_vdate = Date(Dict('post_date', default=None), default=NotAvailable)
            obj_amount = Eval(lambda x: -float_to_decimal(x), Dict('amount'))
            obj_original_currency = Dict('foreign_details/iso_alpha_currency_code', default=NotAvailable)

            def obj_original_amount(self):
                # amount in the account's currency
                amount = Field("amount")(self)
                # amount in the transaction's currency
                original_amount = Dict('foreign_details/amount', default=NotAvailable)(self)
                if not original_amount:
                    return NotAvailable
                else:
                    original_amount = abs(parse_decimal(original_amount))
                if amount < 0:
                    return -original_amount
                else:
                    return original_amount

            #obj__ref = Dict('reference_id')
            obj__ref = Dict('identifier')
