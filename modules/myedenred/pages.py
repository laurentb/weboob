# -*- coding: utf-8 -*-

# Copyright(C) 2017      Théo Dorée
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

from weboob.browser.pages import HTMLPage, LoggedPage, JsonPage, RawPage
from weboob.browser.elements import ItemElement, method, DictElement
from weboob.browser.filters.standard import (
    CleanText, CleanDecimal, Currency, Field, Eval,
    Date, Regexp,
)
from weboob.browser.filters.json import Dict
from weboob.capabilities.bank import Account, Transaction
from weboob.tools.json import json
from weboob.tools.compat import urlparse, parse_qs


class HomePage(HTMLPage):
    def get_href_randomstring(self, filename):
        # The filename has a random string like `3eacdd2f` that changes often
        # (at least once a week).
        # We can get this string easily because file path is always like that:
        # `/js/<filename>.<randomstring>.js`
        #
        # We can't use Regexp(Link(..)) because all the links are in the <head>
        # tag on the page. That would require to do something like  `//link[25]`
        # to get the correct link, and if they modify/add/remove one link then the
        # regex is going to crash or give us the wrong result.
        href = re.search(r'link href=/js/%s.(\w+).js' % filename, self.text)
        return href.group(1)


class JsParamsPage(RawPage):
    def get_json_content(self):
        json_data = re.search(r"JSON\.parse\('(.*)'\)", self.text)
        return json.loads(json_data.group(1))


class JsUserPage(RawPage):
    def get_json_content(self):
        # The regex below will match the JSON by searching for at least one
        # key in it (code_challenge). This JSON is available only one time in the
        # file, so there is no risk of duplicates.
        json_data = re.search(r'({[^{}]+code_challenge:[^{}]+})', self.text).group(1)
        # Delete values that are variables concatenation (like `r + "/connect"`),
        # we do not need them.
        json_data = re.sub(r':([^{\",]+\+)', ':', json_data)
        # There are values without quotes in the json, so we add quotes for the
        # json.loads to work.
        json_data = re.sub(r':([^\",+]+)', r':"\1"', json_data)
        # Keys do not have quotes, adding them for the json.loads to work
        json_data = re.sub(r'([^{\",+]+):', r'"\1":', json_data)
        return json.loads(json_data)


class JsAppPage(RawPage):
    def get_code_verifier(self):
        return re.search(r'code_verifier:"([^"]+)', self.text).group(1)


class InitLoginPage(HTMLPage):
    pass


class LoginPage(HTMLPage):
    def get_json_model(self):
        return json.loads(CleanText('//script[@id="modelJson"]', replace=[('&quot;', '"')])(self.doc))


class ConnectCodePage(LoggedPage, HTMLPage):
    def get_code(self):
        return parse_qs(urlparse(self.url).query)['code'][0]


class TokenPage(LoggedPage, JsonPage):
    def get_access_token(self):
        return CleanText(Dict('access_token'))(self.doc)


class AccountsPage(LoggedPage, JsonPage):
    @method
    class iter_accounts(DictElement):
        item_xpath = 'data'

        class item(ItemElement):
            klass = Account

            def condition(self):
                return CleanText(Dict('status'))(self) == 'active'

            obj_type = Account.TYPE_CARD
            obj_label = obj_id = obj_number = CleanText(Dict('card_ref'))
            # The amount has no `.` or `,` in it. In order to get the amount we have
            # to divide the amount we retrieve by 100 (like the website does).
            obj_balance = Eval(lambda x: x / 100, CleanDecimal(Dict('balances/0/remaining_amount')))
            obj_currency = Currency(Dict('balances/0/currency'))
            obj_cardlimit = Eval(lambda x: x / 100, CleanDecimal(Dict('balances/0/daily_remaining_amount')))
            obj__card_class = CleanText(Dict('class'))
            obj__account_ref = CleanText(Dict('account_ref'))


class TransactionsPage(LoggedPage, JsonPage):
    @method
    class iter_transactions(DictElement):
        item_xpath = 'data'

        class item(ItemElement):
            klass = Transaction

            def condition(self):
                return CleanText(Dict('status'))(self) != 'failed'

            obj_date = Date(Dict('date'))
            obj_raw = CleanText(Dict('outlet/name'))
            obj_amount = Eval(lambda x: x / 100, CleanDecimal(Dict('amount')))

            def obj_label(self):
                # Raw labels can be like this :
                # PASTA ANGERS,FRA
                # O SEIZE - 16 RUE D ALSACE, ANGERS,49100,FRA
                # SFR DISTRIBUTION-23-9.20-0.00-2019
                # The regexp is to get the part with only the name
                # The .strip() is to remove any leading whitespaces due to the ` ?-`
                return Regexp(CleanText(Dict('outlet/name')), r'([^,-]+)(?: ?-|,).*')(self).strip()

            def obj_type(self):
                if Field('amount')(self) < 0:
                    return Transaction.TYPE_CARD
                return Transaction.TYPE_TRANSFER
