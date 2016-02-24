# -*- coding: utf-8 -*-

# Copyright(C) 2012-2020  Budget Insight
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


from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.filters.standard import CleanDecimal, CleanText, Env, Format, Regexp, Async, AsyncLoad
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.html import Attr
from weboob.capabilities.bill import Bill, Subscription
from weboob.capabilities.base import NotAvailable
from weboob.tools.date import parse_french_date


class LoginPage(HTMLPage):
    def login(self, login, password):
        form = self.get_form('//form[@id="log_form"]')
        form['login'] = login
        form['pass'] = password
        form.submit()


class HomePage(LoggedPage, HTMLPage):
    @method
    class get_list(ListElement):
        class item(ItemElement):
            klass = Subscription

            load_details = Attr('//div[@id="abonnenav"]//a[contains(text(), "Modifier mes informations")]', 'href') & AsyncLoad

            obj_subscriber = CleanText('//div[@class="infos_abonne"]/ul/li[1]')
            obj_id = Env('email')
            obj_label = Env('email')

            def parse(self, el):
                self.env['email'] = Async('details', Attr('//input[@name="email"]', 'value'))(self)
                self.page.browser.email = self.env['email']


class DocumentsPage(LoggedPage, HTMLPage):
    def get_list(self):
        sub = Subscription()
        sub.subscriber = self.browser.username
        sub.id = self.browser.username
        sub.label = self.browser.username
        yield sub

    @method
    class get_documents(ListElement):
        item_xpath = '//ul[@class="pane"]/li'

        class item(ItemElement):
            klass = Bill

            obj_id = Format('%s_%s', Env('email'), Regexp(Attr('./span[3]/a', 'href'), '(?<=.facture=)([^*]+)'))
            obj__url = Attr('./span[3]/a', 'href', default=NotAvailable)
            obj_date = Env('date')
            obj_format = u"pdf"
            obj_label = Format('Facture - %s', CleanText('./span[1]/strong'))
            obj_type = u"bill"
            obj_price = CleanDecimal(CleanText('./span[2]/strong'))
            obj_currency = u"€"

            def parse(self, el):
                self.env['email'] = self.page.browser.email
                self.env['date'] = parse_french_date(CleanText('./span[1]/strong')(self)).date()
