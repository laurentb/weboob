# -*- coding: utf-8 -*-

# Copyright(C) 2018      Vincent A
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

from decimal import Decimal

from weboob.browser.pages import LoggedPage, JsonPage
from weboob.browser.elements import method, DictElement, ItemElement
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import Eval
from weboob.capabilities.bank import Account


def float_to_decimal(v):
    return Decimal(str(v))


class LoginPage(JsonPage):
    def get_token(self):
        return self.doc['detail']['token']


class AccountsPage(LoggedPage, JsonPage):
    ENCODING = 'utf-8' # chardet is shit

    @method
    class iter_accounts(DictElement):
        item_xpath = 'detail'

        class item(ItemElement):
            klass = Account

            obj_id = Eval(str, Dict('id'))
            obj_label = Dict('name')
            obj_balance = Eval(float_to_decimal, Dict('current_value'))
            obj_valuation_diff = Eval(float_to_decimal, Dict('absolute_performance'))
            obj_currency = 'EUR'
            obj_type = Account.TYPE_LIFE_INSURANCE


class AccountPage(LoggedPage, JsonPage):
    def get_invest_key(self):
        return self.doc['detail']['project_kind'], self.doc['detail']['risk_level']

    def get_kind(self):
        return self.doc['detail']['project_kind']

    def get_risk(self):
        return self.doc['detail']['risk_level']


class HistoryPage(LoggedPage, JsonPage):
    pass


class InvestPage(LoggedPage, JsonPage):
    ENCODING = 'utf-8'

    def get_invest(self, kind, risk):
        for pk in self.doc['portfolios']:
            if pk['kind'] == kind:
                break
        else:
            assert False

        for p in pk['target_portfolios']:
            if p['risk_id'] == risk:
                break
        else:
            assert False

        for line in p['lines']:
            yield {
                'isin': line['isin'],
                'name': line['name'],
                'share': float_to_decimal(line['weight']) / 100,
            }
