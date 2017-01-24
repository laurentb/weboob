# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Vincent Paredes
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

import re

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.capabilities.bill import Subscription
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import CleanDecimal, CleanText, Env, Field, Regexp, Date, Currency
from weboob.browser.filters.html import Link
from weboob.browser.filters.javascript import JSValue
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.bill import Bill
from weboob.tools.date import parse_french_date


class ProfilPage(HTMLPage):
    pass


class BillsPage(LoggedPage, HTMLPage):
    @method
    class get_documents(ListElement):
        item_xpath = '//div[has-class("factures-historique")]//table//tr[not(ancestor::thead)]'

        class item(ItemElement):
            klass = Bill

            def obj_id(self):
                return '%s_%s' % (Env('subid')(self), Field('date')(self).strftime('%d%m%Y'))

            obj_url = Link('.//td[@headers="ec-downloadCol"]/a', default=NotAvailable)
            obj_date = Date(CleanText('.//td[@headers="ec-dateCol"]'), parse_func=parse_french_date, dayfirst=True)
            obj_label = CleanText('.//td[@headers="ec-dateCol"]')
            obj_format = u"pdf"
            obj_type = u"bill"
            obj_price = CleanDecimal('.//td[@headers="ec-amountCol"]', replace_dots=True)
            obj_currency = Currency('.//td[@headers="ec-amountCol"]')


class SubscriptionsPage(LoggedPage, HTMLPage):
    def build_doc(self, data):
        data = data.decode(self.encoding)
        for line in data.split('\n'):
            mtc = re.match('necFe.bandeau.container.innerHTML\s*=\s*stripslashes\((.*)\);$', line)
            if mtc:
                html = JSValue().filter(mtc.group(1)).encode(self.encoding)
                return super(SubscriptionsPage, self).build_doc(html)

    @method
    class iter_subscription(ListElement):
        item_xpath = '//ul[@id="contractContainer"]//a[starts-with(@id,"carrousel-")]'

        class item(ItemElement):
            klass = Subscription

            obj_id = Regexp(Link('.'), r'\bidContrat=(\d+)', default='')
            obj__page = Regexp(Link('.'), r'\bpage=([^&]+)', default='')
            obj_label = CleanText('.')

            def validate(self, obj):
                # unsubscripted contracts may still be there, skip them else
                # facture-historique could yield wrong bills
                return bool(obj.id) and obj._page != 'nec-tdb-ouvert'

