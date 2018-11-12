# -*- coding: utf-8 -*-

# Copyright(C) 2018      Simon Rochwerg
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

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.elements import method, ItemElement, ListElement
from weboob.browser.filters.standard import CleanText, CleanDecimal, Format, Currency, Date
from weboob.capabilities.bank import Account, Transaction
from weboob.browser.filters.html import Attr
from weboob.capabilities.profile import Profile


class LoginPage(HTMLPage):

    def login(self, login, password):
        form = self.get_form('//form[@class="form-horizontal"]')
        form['Login'] = login
        form['Password'] = password
        form.submit()


class ErrorPage(HTMLPage):
    def get_error(self):
        alert = CleanText('//td/div[@class="editorialContent"]|//div[has-class("blockMaintenance")]/table//p[contains(text(), "password")]')(self.doc)
        if alert:
            return alert


class ProfilePage(LoggedPage, HTMLPage):
    @method
    class get_profile(ItemElement):
        klass = Profile

        obj_name = CleanText('//*[@id="navAffiliationInfos"]/ul/li[1]')
        obj_address = CleanText('//*[@id="1a"]/div[2]/div/div[1]/span')
        obj_email = Attr('//*[@id="Email"]', 'value')


class TermPage(HTMLPage):
    pass


class UnexpectedPage(HTMLPage):
    def get_error(self):
        alert = CleanText('//div[@class="blockMaintenance mainBlock"]/table//td/h3')(self.doc)
        if alert:
            return alert


class AccountPage(LoggedPage, HTMLPage):
    @method
    class get_accounts(ListElement):
        item_xpath = '//div[@id="desktop-data-tables"]/table//tr'

        class item(ItemElement):
            klass = Account

            def obj_id(self):
                _id = CleanText('./td[1]')(self)
                _id = ''.join(i for i in _id if i.isdigit())
                return _id

            def obj_label(self):
                label = Format('%s', CleanText('./td[2]'))(self)
                label = label.replace(" o ", " ")
                return label

            obj__login = CleanDecimal('./td[1]')
            obj_currency = Currency('./td[6]')
            obj__company = CleanText('./td[3]')
            obj_balance = CleanDecimal('./td[6]', replace_dots=True)
            obj_type = Account.TYPE_PERP


class HistoryPage(LoggedPage, HTMLPage):
    @method
    class iter_history(ListElement):
        item_xpath = '//div[@class="accordion_container"]//div[@class="accordion_head-container"]'

        class item(ItemElement):
            klass = Transaction

            def obj_id(self):
                label = CleanText(Attr('./a[contains(@class, "accordion_collapse")]', "id"))(self)
                label = ''.join(i for i in label if i.isdigit())
                return label

            obj_date = Date(CleanText('./div[contains(@class, "accordion_header")]/div[1]/p'))
            obj_category = CleanText('./div[contains(@class, "accordion_header")]/div[2]/p[1]')
            obj_label = CleanText('./div[contains(@class, "accordion_header")]/div[3]/p[1]')
            obj_amount = CleanDecimal('./div[contains(@class, "accordion_header")]/div[6]')
            obj__currency = Currency('./div[contains(@class, "accordion_header")]/div[6]')
