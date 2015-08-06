# -*- coding: utf-8 -*-
# Copyright(C) 2010-2015 Bezleputh
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

from decimal import Decimal
import re

from weboob.capabilities.messages import CantSendMessage

from weboob.capabilities.bill import Bill, Subscription
from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.filters.standard import CleanDecimal, CleanText, Env, Format, Date, Regexp
from weboob.browser.elements import ListElement, ItemElement, method


class LoginPage(HTMLPage):
    def login(self, login, password):
        form = self.get_form('//form[@id="log_data"]')
        form['username'] = login
        form['password'] = password
        form.submit()


class HomePage(HTMLPage, LoggedPage):
    @method
    class get_list(ListElement):
        class item(ItemElement):
            klass = Subscription

            obj_label = CleanText('//span[@class="ecconumteleule"]')
            obj_subscriber = CleanText('//span[@class="economligneaseule eccobold"]')
            obj_id = Env('id')

            def parse(self, el):
                self.env['id'] = re.sub(r'[^\d\-\.]', '', el.xpath('//span[@class="ecconumteleule"]')[0].text)


class SendSMSPage(HTMLPage):
    def send_sms(self, message, receivers):
        sms_number = CleanDecimal(Regexp(CleanText('//span[@class="txt12-o"][1]/strong'), '(\d*) SMS.*'))(self.doc)
        if sms_number == 0:
            msg = CleanText('//span[@class="txt12-o"][1]')(self.doc)
            raise CantSendMessage(msg)

        form = self.get_form('//form[@name="formSMS"]')
        form["fieldMsisdn"] = receivers
        form["fieldMessage"] = message.content
        form.submit()


class SendSMSErrorPage(HTMLPage):
    def get_error_message(self):
        return CleanText('//span[@class="txt12-o"][1]')(self.doc)


class BillsPage(HTMLPage):
    @method
    class get_bills(ListElement):
        item_xpath = '//table[@class="ecconotif historique"]/tbody/tr'

        class item(ItemElement):
            klass = Bill

            obj_id = Format('%s.%s', Env('subid'), Env('id'))
            obj__id_bill = Env('id')
            obj_date = Date(CleanText('./td[1]/span'), dayfirst=True)
            obj_format = u"pdf"
            obj_price = Env('price')

            def parse(self, el):
                try:
                    deci = Decimal(el.xpath('./td[2]//span[@class="priceCT"]')[0].text) / 100
                except IndexError:
                    deci = 0
                self.env['price'] = Decimal(el.xpath('./td[2]/span')[0].text) + deci
                onclick = el.xpath('.//td[@class="visuFacture"]/span/a/@onclick')[0]
                self.env['id'] = re.findall(r'\d\d+', onclick)[0]
