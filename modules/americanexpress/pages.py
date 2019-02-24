# -*- coding: utf-8 -*-

# Copyright(C) 2017 Vincent Ardisson
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from ast import literal_eval
from decimal import Decimal
import re

from weboob.browser.pages import LoggedPage, JsonPage, HTMLPage
from weboob.browser.elements import ItemElement, DictElement, method
from weboob.browser.filters.standard import Date, Eval, CleanText, Field, CleanDecimal
from weboob.browser.filters.json import Dict
from weboob.capabilities.bank import Account, Transaction
from weboob.capabilities.base import NotAvailable
from weboob.tools.json import json
from weboob.tools.compat import basestring
from weboob.exceptions import ActionNeeded, BrowserUnavailable


def float_to_decimal(f):
    return Decimal(str(f))

def parse_decimal(s):
    # we might get 1,399,680 in rupie indonésienne
    if s.count(',') > 1 and not s.count('.'):
        return CleanDecimal(replace_dots=(',', '.')).filter(s)
    # we don't know which decimal format this account will use
    comma = s.rfind(',') > s.rfind('.')
    return CleanDecimal(replace_dots=comma).filter(s)


class WrongLoginPage(HTMLPage):
    pass


class AccountSuspendedPage(HTMLPage):
    pass


class NoCardPage(HTMLPage):
    def on_load(self):
        raise ActionNeeded()


class NotFoundPage(HTMLPage):
    def on_load(self):
        alert_header = CleanText('//h1[@class="alert-header"]/span')(self.doc)
        alert_content = CleanText('//p[@class="alert-subtitle"]/span')(self.doc)
        raise BrowserUnavailable(alert_header, alert_content)


class LoginPage(HTMLPage):
    def login(self, username, password):
        form = self.get_form(name='ssoform')
        form['UserID'] = username
        form['USERID'] = username
        form['Password'] = password
        form['PWD'] = password
        form.submit()


class AccountsPage(LoggedPage, HTMLPage):
    def iter_accounts(self):
        for line in self.doc.xpath('//script[@id="initial-state"]')[0].text.split('\n'):
            m = re.search('window.__INITIAL_STATE__ = (.*);', line)
            if m:
                data = json.loads(literal_eval(m.group(1)))
                break
        else:
            assert False, "data was not found"

        assert data[13] == 'core'
        assert len(data[14]) == 3

        # search for products to get products list
        for index, el in enumerate(data[14][2]):
            if 'products' in el:
                accounts_data = data[14][2][index+1]

        assert len(accounts_data) == 2
        assert accounts_data[1][4] == 'productsList'

        accounts_data = accounts_data[1][5]
        token = []

        for account_data in accounts_data:
            if isinstance(account_data, basestring):
                balances_token = account_data

            elif isinstance(account_data, list) and not account_data[4][2][0]=="Canceled":
                acc = Account()
                if len(account_data) > 15:
                    token.append(account_data[-11])
                    acc._idforJSON =  account_data[10][-1]
                else:
                    acc._idforJSON = account_data[-5][-1]
                acc._idforJSON = re.sub('\s+', ' ', acc._idforJSON)
                acc.number = '-%s' % account_data[2][2]
                acc.label = '%s %s' % (account_data[6][4], account_data[10][-1])
                acc._balances_token = acc.id = balances_token
                acc._token = token[-1]
                acc.type = Account.TYPE_CARD
                yield acc


class JsonBalances(LoggedPage, JsonPage):
    def set_balances(self, accounts):
        by_token = {a._balances_token: a for a in accounts}
        for d in self.doc:
            # coming is what should be refunded at a futur deadline
            by_token[d['account_token']].coming = -float_to_decimal(d['total_debits_balance_amount'])
            # balance is what is currently due
            by_token[d['account_token']].balance = -float_to_decimal(d['remaining_statement_balance_amount'])


class JsonBalances2(LoggedPage, JsonPage):
    def set_balances(self, accounts):
        by_token = {a._balances_token: a for a in accounts}
        for d in self.doc:
            by_token[d['account_token']].balance = -float_to_decimal(d['total']['payments_credits_total_amount'])
            by_token[d['account_token']].coming = -float_to_decimal(d['total']['debits_total_amount'])
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

            obj_raw = CleanText(Dict('description', default=''))
            obj_date = Date(Dict('statement_end_date', default=None), default=None)
            obj_rdate = Date(Dict('charge_date'))
            obj_vdate = Date(Dict('post_date', default=None), default=NotAvailable)
            obj_amount = Eval(lambda x: -float_to_decimal(x), Dict('amount'))
            obj_original_currency = Dict('foreign_details/iso_alpha_currency_code', default=NotAvailable)
            obj_commission = CleanDecimal(Dict('foreign_details/commission_amount', default=NotAvailable), sign=lambda x: -1, default=NotAvailable)
            obj__owner = CleanText(Dict('embossed_name'))
            obj_id = Dict('reference_id', default=NotAvailable)

            def obj_original_amount(self):
                # amount in the account's currency
                amount = Field("amount")(self)
                # amount in the transaction's currency
                original_amount = Dict('foreign_details/amount', default=NotAvailable)(self)
                if Field("original_currency")(self) == "XAF":
                    original_amount = abs(CleanDecimal(replace_dots=('.')).filter(original_amount))
                elif not original_amount:
                    return NotAvailable
                else:
                    original_amount = abs(parse_decimal(original_amount))
                if amount < 0:
                    return -original_amount
                else:
                    return original_amount

            # obj__ref = Dict('reference_id')
            obj__ref = Dict('identifier')

