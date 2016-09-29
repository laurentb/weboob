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


import json

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.capabilities.bill import Subscription
from weboob.browser.elements import ListElement, ItemElement, SkipItem, method
from weboob.browser.filters.standard import CleanDecimal, CleanText, Env, Format, Regexp, Date, Async, AsyncLoad, BrowserURL
from weboob.browser.filters.html import Attr, Link
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.bill import Bill


class ProfilPage(HTMLPage):
    pass


class BillsPage(LoggedPage, HTMLPage):
    @method
    class get_list(ListElement):
        def parse(self, el):
            if self.page.doc.xpath('//div[@ecareurl]'):
                self.item_xpath = '//div[@ecareurl]'

        class item(ItemElement):
            klass = Subscription

            load_details = BrowserURL('profilpage') & AsyncLoad

            obj_subscriber = Env('subscriber')
            obj_label = Env('subid')
            obj_id = obj_label
            obj__multi = Env('multi')

            def parse(self, el):
                subscriber = Async('details', CleanText(u'//span[contains(text(), "prénom / nom")]/following-sibling::span[1]'))(self)
                self.env['subscriber'] = subscriber if subscriber else \
                                         Async('details', Format('%s %s %s', \
                                         CleanText(u'//*[contains(text(), "civilité")]/following-sibling::*[1]'), \
                                         CleanText(u'//*[contains(text(), "prénom")]/following-sibling::*[1]'), \
                                         CleanText(u'//*[text() = "nom :"]/following-sibling::*[1]')))(self)
                subid = Regexp(Attr('.', 'ecareurl', default="None"), 'idContrat=(\d+)', default=None)(self)
                self.env['subid'] = subid if subid else self.page.browser.username
                self.env['multi'] = True if subid else False

                # Prevent from available account but no added in customer area
                if subid and not json.loads(self.page.browser.open(Attr('.', 'ecareurl')(self)).content)['html']:
                    raise SkipItem()

    @method
    class get_documents(ListElement):
        item_xpath = '//ul[has-class("factures")]/li'

        class item(ItemElement):
            klass = Bill

            obj_id = Format('%s_%s', Env('subid'), CleanDecimal(CleanText('.//span[has-class("date")]')))
            obj_url = Link('.//span[has-class("pdf")]/a', default=NotAvailable)
            obj_date = Date(CleanText('.//span[has-class("date")]'), dayfirst=True)
            obj_label = CleanText('.//span[has-class("date")]')
            obj_format = u"pdf"
            obj_type = u"bill"
            obj_price = CleanDecimal('span[@class="montant"]', replace_dots=True)

            def obj_currency(self):
                return Bill.get_currency(CleanText('span[@class="montant"]')(self))
