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
from weboob.browser.filters.html import Link
from weboob.browser.elements import DictElement, ItemElement, ListElement, method
from weboob.tools.date import parse_french_date


class LoginPage(HTMLPage):
    def login(self, login, password):
        form = self.get_form('//form[@id="log_data"]')
        form['username'] = login
        form['password'] = password
        form.submit()


class HomePage(HTMLPage, LoggedPage):
    pass


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

            def parse(self, el):
                # add spaces
                number = iter(self.obj_id(el))
                self.env['label'] = ' '.join(a+b for a, b in zip(number, number))


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
    def get_ref(self, label):
        options = self.doc.xpath('//select[@id="factureMois"]/option[position() > 1]/@value')
        for option in options:
            ref = self.doc.xpath('//span[contains(text(), "%s")]/ \
                ancestor::div[has-class("etape-content")]//a[@id="btnAnciennesFactures"]' % label)
            if ref:
                # Get ref and return it
                return re.search('reference=([\d]+)', Link().filter(ref)).group(1)
            self.doc = self.browser.open('%s?mois=%s' % (self.browser.url, option)).page.doc
        return None

    @method
    class get_documents(ListElement):
        item_xpath = '//div[@facture-id]'

        class item(ItemElement):
            klass = Bill

            obj__ref = CleanText('//input[@id="noref"]/@value')
            obj_id = Format('%s_%s', Env('subid'), CleanText('./@facture-id'))
            obj_url = Format(u'http://www.bouyguestelecom.fr/parcours/facture/download/index?id=%s', CleanText('./@facture-id'))
            obj_date = Env('date')
            obj_format = u"pdf"
            obj_label = CleanText('./text()')
            obj_type = u"bill"
            obj_price = CleanDecimal(CleanText('./span', replace=[(u' € ', '.')]))
            obj_currency = u"€"

            def parse(self, el):
                self.env['date'] = parse_french_date('01 %s' % CleanText('./text()')(self)).date()
