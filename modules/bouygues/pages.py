# -*- coding: utf-8 -*-

# Copyright(C) 2019      Budget Insight
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

import re
from datetime import timedelta

from weboob.browser.elements import DictElement, ItemElement, method
from weboob.browser.filters.json import Dict
from weboob.browser.pages import HTMLPage, JsonPage, LoggedPage, RawPage
from weboob.capabilities import NotAvailable
from weboob.capabilities.bill import Subscription, Bill
from weboob.browser.filters.standard import Date, CleanDecimal, Env, Format


class LoginPage(HTMLPage):
    def login(self, username, password):
        form = self.get_form()
        form['username'] = username
        form['password'] = password
        form.submit()


class AppConfigPage(JsonPage):
    def get_client_id(self):
        return self.doc['config']['oauth']['clientId']


class SubscriberPage(LoggedPage, JsonPage):
    def get_subscriber(self):
        assert self.doc['type'] in ('INDIVIDU', 'ENTREPRISE'), "%s is unknown" % self.doc['type']

        if self.doc['type'] == 'INDIVIDU':
            subscriber_dict = self.doc
        elif self.doc['type'] == 'ENTREPRISE':
            subscriber_dict = self.doc['representantLegal']

        return '%s %s %s' % (subscriber_dict['civilite'], subscriber_dict['prenom'], subscriber_dict['nom'])


class SubscriptionDetail(LoggedPage, JsonPage):
    def get_label(self):
        label_list = []
        for s in self.doc['items']:
            if 'numeroTel' in s:
                phone = re.sub(r'^\+\d{2}', '0', s['numeroTel'])
                label_list.append(' '.join([phone[i:i + 2] for i in range(0, len(phone), 2)]))
            else:
                continue

        return ' - '.join(label_list)


class SubscriptionPage(LoggedPage, JsonPage):
    @method
    class iter_subscriptions(DictElement):
        item_xpath = 'items'

        class item(ItemElement):
            klass = Subscription

            obj_id = Dict('id')
            obj_url = Dict('_links/factures/href')


class MyDate(Date):
    """
    some date are datetime and contains date at GMT, and always at 22H or 23H
    but date inside PDF file is at GMT +1H or +2H (depends of summer or winter hour)
    so we add one day and skip time to get good date
    """
    def filter(self, txt):
        date = super(MyDate, self).filter(txt)
        if date:
            date += timedelta(days=1)
        return date


class DocumentPage(LoggedPage, JsonPage):
    @method
    class iter_documents(DictElement):
        item_xpath = 'items'

        class item(ItemElement):
            klass = Bill

            obj_id = Format('%s_%s', Env('subid'), Dict('idFacture'))
            obj_price = CleanDecimal(Dict('mntTotFacture'))
            obj_url = Dict('_links/facturePDF/href')
            obj_date = MyDate(Dict('dateFacturation'))
            obj_duedate = MyDate(Dict('dateLimitePaieFacture', default=NotAvailable), default=NotAvailable)
            obj_label = Format('Facture %s', Dict('idFacture'))
            obj_format = 'pdf'
            obj_currency = 'EUR'


class DocumentDownloadPage(LoggedPage, JsonPage):
    def on_load(self):
        # this url change each time we want to download document, (the same one or another)
        self.browser.location(self.doc['_actions']['telecharger']['action'])


class DocumentFilePage(LoggedPage, RawPage):
    # since url of this file is almost the same than url of DocumentDownloadPage (which is a JsonPage)
    # we have to define it to avoid mismatching
    pass
