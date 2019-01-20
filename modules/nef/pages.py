# -*- coding: utf-8 -*-

# Copyright(C) 2019      Damien Cassou
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

from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import CleanText, CleanDecimal, Regexp, Field
from weboob.browser.pages import HTMLPage, PartialHTMLPage, LoggedPage

from weboob.capabilities.bank import Account

class LoginPage(HTMLPage):
    def login(self, username, password):
        form = self.get_form(name='formSignon')
        form['userId'] = username
        form['logonId'] = username
        form['static'] = password
        form.submit()

class HomePage(LoggedPage, HTMLPage):
    pass

class AccountsPage(LoggedPage, PartialHTMLPage):
    ACCOUNT_TYPES = {re.compile('livret'):           Account.TYPE_SAVINGS,
                     re.compile('parts sociales'):   Account.TYPE_SAVINGS,
                    }

    @method
    class get_items(ListElement):
        item_xpath = '//div[@data-type="account"]'

        class item(ItemElement):
            klass = Account

            obj_id = CleanText('.//div/div/div[(position()=3) and (has-class("pc-content-text"))]/span') & Regexp(pattern=r'(\d+) ')
            obj_label = CleanText('.//div/div/div[(position()=2) and (has-class("pc-content-text-wrap"))]')
            obj_balance = CleanDecimal('./div[position()=3]/span', replace_dots=True)
            obj_currency = u'EUR'

            def obj_type(self):
                label = Field('label')(self).lower()

                for regex, account_type in self.page.ACCOUNT_TYPES.items():
                    if (regex.match(label)):
                        return account_type

                return Account.TYPE_UNKNOWN
