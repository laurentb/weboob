# -*- coding: utf-8 -*-

# Copyright(C) 2015      Vincent Paredes
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

from weboob.capabilities.bill import Bill, Subscription
from weboob.browser.pages import HTMLPage, LoggedPage, JsonPage
from weboob.browser.filters.standard import CleanDecimal, CleanText, Env, Format, Date
from weboob.browser.filters.html import Attr
from weboob.browser.filters.json import Dict
from weboob.browser.elements import ListElement, ItemElement, method, DictElement
from weboob.exceptions import ActionNeeded, AuthMethodNotImplemented


class LoginPage(HTMLPage):
    def on_load(self):
        if self.doc.xpath('//p[contains(text(), "You have activated the double factor authentication")]'):
            raise AuthMethodNotImplemented('Two-Factor authentication is not supported.')

    def is_logged(self):
        return not self.doc.xpath('//div[has-class("error")]') and not self.doc.xpath('//form//input[contains(@placeholder, "Account ID")]')

    def login(self, login, password):
        form = self.get_form('//form[@class="pagination-centered"]')
        user = Attr(None, 'name').filter(self.doc.xpath('//input[contains(@placeholder, "Account ID")]'))
        pwd = Attr(None, 'name').filter(self.doc.xpath('//input[@placeholder="Password"]'))
        form[user] = login
        form[pwd] = password
        form.submit()

    # There is 2 double auth method
    # One activated by the user, that we don't handle,
    # The other, spawning sometimes at first login, that we can handle.

    def check_user_double_auth(self):
        double_auth = self.doc.xpath('//input[@id="codeSMS"]')

        if double_auth:
            raise ActionNeeded(CleanText('(//div[contains(., "Two-Factor")])[5]')(self.doc))

    def check_website_double_auth(self):
        double_auth = self.doc.xpath('//input[@id="emailCode"]')

        return bool(double_auth)

    def get_otp_message(self):
        return self.doc.xpath('//div[@class="control-group" and contains(., "email")]')

    def get_security_form(self):
        return self.get_form()


class ProfilePage(LoggedPage, JsonPage):
    @method
    class get_subscriptions(ListElement):
        class item(ItemElement):
            klass = Subscription

            obj_label = CleanText(Dict('nichandle'))
            obj_subscriber = Format("%s %s", CleanText(Dict('firstname')), CleanText(Dict('name')))
            obj_id = CleanText(Dict('nichandle'))


class BillsPage(LoggedPage, JsonPage):
    @method
    class get_documents(DictElement):
        item_xpath = 'list/results'

        class item(ItemElement):
            klass = Bill

            obj_id = Format('%s.%s', Env('subid'), Dict('orderId'))
            obj_date = Date(Dict('billingDate'))
            obj_format = 'pdf'
            obj_price = CleanDecimal(Dict('priceWithTax/value'))
            obj_url = Dict('pdfUrl')
            obj_label = Format('Facture %s', Dict('orderId'))
