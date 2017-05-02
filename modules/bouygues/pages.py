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
from weboob.browser.filters.standard import CleanDecimal, CleanText, Env, Format, Regexp, Field
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

            obj__type = CleanText(Dict('type'))
            obj_label = Env('label')
            obj_subscriber = Format("%s %s %s", CleanText(Dict('civilite')),
                                    CleanText(Dict('prenom')), CleanText(Dict('nom')))

            def obj_id(self):
                if Dict('date-activation')(self) is not None:
                    return Format('%s-%s', Dict('num_ligne'), Dict('date-activation'))(self)
                else:
                    return Format('%s', Dict('num_ligne'))(self)

            def parse(self, el):
                # add spaces
                number = iter(Field('id')(self).split('-')[0])
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
            for ctr in self.doc.xpath('//div[has-class("eccoetape")]'):
                if ctr.xpath('.//span[contains(text(), $label)]', label=label):
                    ref = ctr.xpath('.//a[@id="btnAnciennesFactures"]')
                    if ref:
                        return re.search('reference=([\d]+)', Link().filter(ref)).group(1)

            self.logger.debug("couldn't find ref this month, retrying with %s", option)
            self.doc = self.browser.open('%s?mois=%s' % (self.browser.url, option)).page.doc
        return None

    @method
    class get_documents(ListElement):
        item_xpath = '//div[@facture-id]'

        class item(ItemElement):
            klass = Bill

            obj__ref = CleanText('//input[@id="noref"]/@value')
            obj_id = Format('%s_%s', Env('subid'), CleanText('./@facture-id'))
            obj_url = Format('http://www.bouyguestelecom.fr/parcours/facture/download/index?id=%s&no_reference=%s', CleanText('./@facture-id'), CleanText('./@facture-ligne'))
            obj_date = Env('date')
            obj_format = u"pdf"
            obj_label = CleanText('./text()')
            obj_type = u"bill"
            obj_price = CleanDecimal(CleanText('./span', replace=[(u' € ', '.')]))
            obj_currency = u"€"

            def parse(self, el):
                self.env['date'] = parse_french_date('01 %s' % CleanText('./text()')(self)).date()

            def condition(self):
                # XXX ugly fix to avoid duplicate bills
                return CleanText('./@facture-id')(self.el) != CleanText('./following-sibling::div[1]/@facture-id')(self.el)


class UselessPage(HTMLPage):
    pass
