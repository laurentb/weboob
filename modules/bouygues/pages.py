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


import re

from weboob.capabilities.messages import CantSendMessage

from weboob.capabilities.bill import Bill, Subscription
from weboob.browser.pages import HTMLPage, JsonPage, LoggedPage
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import CleanDecimal, CleanText, Env, Format, Regexp
from weboob.browser.elements import DictElement, ItemElement, ListElement, method
from weboob.tools.date import parse_french_date


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

            obj_subscriber = CleanText('//span[@class="economligneaseule eccobold"]')
            obj_id = Env('id')
            obj_label = CleanText('//span[@class="ecconumteleule"]')
            obj__contract = Env('contract')

            def parse(self, el):
                self.env['id'] = re.sub(r'[^\d\-\.]', '', el.xpath('//span[@class="ecconumteleule"]')[0].text)
                self.env['contract'] = re.search("tc_vars\[\"ID_contrat\"\] = '([0-9]+)'", self.page.data).group(1)


class ProfilePage(JsonPage, LoggedPage):
    @method
    class get_list(DictElement):
        item_xpath = 'data/lignes'

        class item(ItemElement):
            klass = Subscription

            obj_id = CleanText(Dict('num_ligne'))
            obj__type = CleanText(Dict('type'))
            obj_label = Env('label')
            obj_subscriber = Format("%s %s %s", CleanText(Dict('civilite')),
                                    CleanText(Dict('prenom')), CleanText(Dict('nom')))
            obj__contract = Env('contract')

            def parse(self, el):
                # add spaces
                number = iter(self.obj_id(el))
                self.env['label'] = ' '.join(a+b for a, b in zip(number, number))
                self.env['contract'] = re.search('\\"user_id\\":\\"([0-9]+)\\"', self.page.get('data.tag')).group(1)


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


class DocumentsPage(HTMLPage):
    @method
    class get_documents(ListElement):
        item_xpath = '//div[@facture-id]'

        class item(ItemElement):
            klass = Bill

            obj__ref = CleanText('//input[@id="noref"]/@value')
            obj_id = Format('%s_%s', Env('user'), CleanText('./@facture-id'))
            obj__url = Format('http://www.bouyguestelecom.fr/parcours/facture/download/index?id=%s', CleanText('./@facture-id'))
            obj_date = Env('date')
            obj_format = u"pdf"
            obj_label = CleanText('./text()')
            obj_type = u"bill"
            obj_price = CleanDecimal(CleanText('./span', replace=[(u' € ', '.')]))
            obj_currency = u"€"

            def parse(self, el):
                self.env['user'] = self.page.browser.subid
                self.env['date'] = parse_french_date(CleanText('./text()')(self)).date()
