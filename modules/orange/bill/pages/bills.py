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
import HTMLParser

from weboob.browser.pages import HTMLPage, LoggedPage, JsonPage
from weboob.capabilities.bill import Subscription
from weboob.browser.elements import DictElement, ListElement, ItemElement, method, TableElement
from weboob.browser.filters.standard import CleanDecimal, CleanText, Env, Field, Regexp, Date, Currency, BrowserURL
from weboob.browser.filters.html import Link, TableCell
from weboob.browser.filters.javascript import JSValue
from weboob.browser.filters.json import Dict
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.bill import Bill
from weboob.tools.date import parse_french_date
from weboob.tools.compat import urlencode


class ProfilPage(HTMLPage):
    pass


class ContractPage(LoggedPage, JsonPage):
    def is_pro(self, subid):
        if self.doc:
            for elem in self.doc:
                if subid == elem['id']:
                    return True


class BillsApiPage(LoggedPage, JsonPage):
    @method
    class get_bills(DictElement):
        item_xpath = 'bills'

        class item(ItemElement):
            klass = Bill

            obj_duedate = Date(Dict('dueDate'), parse_func=parse_french_date, dayfirst=True,  default=NotAvailable)
            obj_price = CleanDecimal(Dict('amountIncludingTax'))
            obj_type = "bill"
            obj_format = "pdf"

            def obj_label(self):
                return "Facture du %s" % Field('duedate')(self)

            def obj_id(self):
                return "%s_%s" % (Env('subid')(self), Field('duedate')(self).strftime('%d%m%Y'))

            def get_params(self):
                params = {'billid': Dict('id')(self), 'billDate': Dict('dueDate')(self)}
                return urlencode(params)

            obj_url = BrowserURL('doc_api', subid=Env('subid'), dir=Dict('documents/0/mainDir'), fact_type=Dict('documents/0/subDir'), billparams=get_params)


class BillsPage(LoggedPage, HTMLPage):

    @method
    class get_bills(TableElement):
        item_xpath = '//table[has-class("table-hover")]/div/div/tr | //table[has-class("table-hover")]/div/tr'
        head_xpath = '//table[has-class("table-hover")]/thead/tr/th'

        col_date = u'Date'
        col_amount = [u'Montant TTC', u'Montant']
        col_ht = u'Montant HT'
        col_url = u'Télécharger'
        col_infos = u'Infos paiement'

        class item(ItemElement):
            klass = Bill

            obj_type = u"bill"
            obj_format = u"pdf"

            # TableCell('date') can have other info like: 'duplicata'
            obj_date = Date(CleanText('./td[@headers="ec-dateCol"]/text()[not(preceding-sibling::br)]'), parse_func=parse_french_date, dayfirst=True)

            def obj__cell(self):
                # sometimes the link to the bill is not in the right column (Thanks Orange!!)
                if CleanText(TableCell('url')(self))(self):
                    return 'url'
                return 'infos'

            def obj_price(self):
                if CleanText(TableCell('amount')(self))(self):
                    return CleanDecimal(Regexp(CleanText(TableCell('amount')), '.*?([\d,]+).*', default=NotAvailable), replace_dots=True, default=NotAvailable)(self)
                else:
                    return Field('_ht')(self)

            def obj_currency(self):
                if CleanText(TableCell('amount')(self))(self):
                    return Currency(TableCell('amount')(self))(self)
                else:
                    return Currency(TableCell('ht')(self))(self)

            # Only when a list of documents is present
            obj__url_base = Regexp(CleanText('.//ul[@class="liste"]/script', default=None), '.*?contentList[\d]+ \+= \'<li><a href=".*\"(.*?idDocument=2)"', default=None)
            def obj_url(self):
                if Field('_url_base')(self):
                    # URL won't work if HTML is not unescape
                    return HTMLParser.HTMLParser().unescape(str(Field('_url_base')(self)))
                else :
                    return Link(TableCell(Field('_cell')(self))(self)[0].xpath('./a'), default=NotAvailable)(self)

            obj__label_base = Regexp(CleanText('.//ul[@class="liste"]/script', default=None), '.*</span>(.*?)</a.*', default=None)

            def obj_label(self):
                if Field('_label_base')(self):
                    return HTMLParser.HTMLParser().unescape(str(Field('_label_base')(self)))
                else:
                    return CleanText(TableCell(Field('_cell')(self))(self)[0].xpath('.//span[@class="ec_visually_hidden"]'))(self)

            obj__ht = CleanDecimal(TableCell('ht', default=NotAvailable), replace_dots=True, default=NotAvailable)
            def obj_vat(self):
                if Field('_ht')(self) is NotAvailable or Field('price')(self) is NotAvailable:
                    return
                return Field('price')(self) - Field('_ht')(self)

            def obj_id(self):
                if Field('price')(self) is NotAvailable:
                    return '%s_%s%s' % (Env('subid')(self), Field('date')(self).strftime('%d%m%Y'), Field('_ht')(self))
                else:
                    return '%s_%s%s' % (Env('subid')(self), Field('date')(self).strftime('%d%m%Y'), Field('price')(self))


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
            obj__is_pro = False

            def validate(self, obj):
                # unsubscripted contracts may still be there, skip them else
                # facture-historique could yield wrong bills
                return bool(obj.id) and obj._page != 'nec-tdb-ouvert'

