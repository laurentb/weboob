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
from datetime import datetime, timedelta

from weboob.capabilities.messages import CantSendMessage

from weboob.capabilities.base import NotLoaded
from weboob.capabilities.bill import Bill, Subscription
from weboob.browser.pages import HTMLPage, JsonPage, LoggedPage, PDFPage
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import CleanDecimal, CleanText, Env, Format, Regexp
from weboob.browser.elements import DictElement, ItemElement, method


class LoginPage(HTMLPage):
    def login(self, login, password, lastname):
        form = self.get_form('//form[@id="log_data"]')

        form['username'] = login
        form['password'] = password

        if 'lastname' in form:
            form['lastname'] = lastname

        form.submit()


class HomePage(LoggedPage, HTMLPage):
    pass


class SubscriberPage(LoggedPage, JsonPage):
    def get_subscriber(self):
        if self.doc['type'] == 'INDIVIDU':
            sub_dict = self.doc
        else:
            sub_dict = self.doc['representantLegal']
        return "%s %s %s" % (sub_dict['civilite'], sub_dict['prenom'], sub_dict['nom'])


class SubscriptionPage(LoggedPage, JsonPage):
    @method
    class iter_subscriptions(DictElement):
        item_xpath = 'items'

        class item(ItemElement):
            klass = Subscription

            obj_id = Dict('id')
            obj_url = Dict('_links/factures/href')
            obj_subscriber = Env('subscriber')


class SubscriptionDetailPage(LoggedPage, JsonPage):
    def get_label(self):
        num_tel_list = []
        for s in self.doc['items']:
            phone = re.sub(r'^\+\d{2}', '0', s['numeroTel'])
            num_tel_list.append(' '.join([phone[i:i + 2] for i in range(0, len(phone), 2)]))

        return ' - '.join(num_tel_list)


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


class DocumentsPage(LoggedPage, JsonPage):
    FRENCH_MONTHS = {
        1: 'Janvier',
        2: 'Février',
        3: 'Mars',
        4: 'Avril',
        5: 'Mai',
        6: 'Juin',
        7: 'Juillet',
        8: 'Août',
        9: 'Septembre',
        10: 'Octobre',
        11: 'Novembre',
        12: 'Décembre',
    }

    @method
    class iter_documents(DictElement):
        item_xpath = 'items'

        class item(ItemElement):
            klass = Bill

            obj_id = Format('%s_%s', Env('subid'), Dict('idFacture'))
            obj_url = Format('https://api.bouyguestelecom.fr%s', Dict('_links/facturePDF/href'))
            obj_date = Env('date')
            obj_duedate = Env('duedate')
            obj_format = u"pdf"
            obj_label = Env('label')
            obj_type = u"bill"
            obj_price = CleanDecimal(Dict('mntTotFacture'))
            obj_currency = u'EUR'

            def parse(self, el):
                bill_date = datetime.strptime(Dict('dateFacturation')(self), "%Y-%m-%dT%H:%M:%SZ").date()

                # dateFacturation is like: 'YYYY-MM-DDTHH:00:00Z' where Z is UTC time and HH 23 in winter and 22 in summer
                # which always correspond to the day after at midnight in French time zone
                # so we remove hour and consider the day after as date (which is also the date inside pdf)
                self.env['date'] = bill_date + timedelta(days=1)

                duedate = Dict('dateLimitePaieFacture', default=NotLoaded)(self)
                if duedate:
                    self.env['duedate'] = datetime.strptime(duedate, "%Y-%m-%dT%H:%M:%SZ").date() + timedelta(days=1)
                else:
                    # for some connections we don't have duedate (why ?)
                    self.env['duedate'] = NotLoaded

                self.env['label'] = "%s %d" % (self.page.FRENCH_MONTHS[self.env['date'].month], self.env['date'].year)

    def get_one_shot_download_url(self):
        return self.doc['_actions']['telecharger']['action']


class UselessPage(HTMLPage):
    pass


class DocumentFilePage(PDFPage):
    pass
