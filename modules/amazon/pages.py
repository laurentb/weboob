# -*- coding: utf-8 -*-

# Copyright(C) 2017      Théo Dorée
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


from weboob.browser.pages import HTMLPage, LoggedPage, FormNotFound
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.standard import (
    CleanText, CleanDecimal, Env, Regexp, Format,
    Field, Currency, RegexpError
)
from weboob.capabilities.bill import Bill, Subscription
from weboob.tools.date import parse_french_date


class HomePage(HTMLPage):
    def get_login_link(self):
        return self.doc.xpath('//a[./span[contains(., "%s")]]/@href' % self.browser.L_SIGNIN)[0]


class PanelPage(HTMLPage, LoggedPage):
    def get_sub_link(self):
        return self.doc.xpath('//a[.//h3[contains(., "%s")]]/@href' % self.browser.L_LOGIN)[0]


class SecurityPage(HTMLPage, LoggedPage):
    def get_otp_message(self):
        message = self.doc.xpath('//div[@class="a-box-inner"]/p')
        return message[0] if message else None

    def send_code(self):
        form = self.get_form()
        form.submit()

    def get_response_form(self):
        try:
            form = self.get_form(id='auth-mfa-form')
            return form
        except FormNotFound:
            form = self.get_form(nr=0)
            return form


class LanguagePage(HTMLPage):
    pass


class HistoryPage(HTMLPage):
    pass


class LoginPage(HTMLPage):
    def login(self, login, password, captcha=None):
        form = self.get_form(name='signIn')

        form['email'] = login
        form['password'] = password
        form['rememberMe'] = "true"

        if captcha:
            form['guess'] = captcha
        form.submit()

    def has_captcha(self):
        return self.doc.xpath('//div[@id="image-captcha-section"]//img[@id="auth-captcha-image"]/@src')

    def get_response_form(self):
        try:
            form = self.get_form(id='auth-mfa-form')
            return form
        except FormNotFound:
            form = self.get_form(nr=0)
            return form


class SubscriptionsPage(LoggedPage, HTMLPage):
    @method
    class get_item(ItemElement):
        klass = Subscription

        def obj_subscriber(self):
            try:
                return Regexp(CleanText('//div[contains(@class, "a-fixed-right-grid-col")]'), self.page.browser.L_SUBSCRIBER)(self)
            except RegexpError:
                return self.page.browser.username

        obj_id = 'amazon'

        def obj_label(self):
            return self.page.browser.username


class DocumentsPage(LoggedPage, HTMLPage):
    @method
    class iter_documents(ListElement):
        item_xpath = '//div[contains(@class, "order") and contains(@class, "a-box-group")]'

        class item(ItemElement):
            klass = Bill

            obj__simple_id = CleanText('.//div[has-class("actions")]//span[has-class("value")]')
            obj_id = Format('%s_%s', Env('subid'), Field('_simple_id'))
            obj_url = Format('/gp/css/summary/print.html/ref=oh_aui_ajax_pi?ie=UTF8&orderID=%s', Field('_simple_id'))
            obj_format = 'html'
            obj_label = Format('Facture %s', Field('_simple_id'))
            obj_type = 'bill'

            def obj_date(self):
                currency = Env('currency')(self)
                return parse_french_date(CleanText('.//div[has-class("a-col-left")]//span[has-class("value") and not(contains(., "%s"))]' % currency)(self))

            def obj_price(self):
                currency = Env('currency')(self)
                return CleanDecimal('.//div[has-class("a-col-left")]//span[has-class("value") and contains(., "%s")]' % currency, replace_dots=currency == u'EUR')(self)

            def obj_currency(self):
                currency = Env('currency')(self)
                return Currency('.//div[has-class("a-col-left")]//span[has-class("value") and contains(., "%s")]' % currency)(self)
