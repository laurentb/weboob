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


import re

from weboob.browser.pages import HTMLPage
from weboob.capabilities.bill import Subscription
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import CleanDecimal, CleanText, Env, Format, Regexp, Date, Async, AsyncLoad, BrowserURL
from weboob.browser.filters.html import Attr
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.bill import Bill


class BillsPage(HTMLPage):
    @method
    class get_list(ListElement):
        class item(ItemElement):
            klass = Subscription

            load_details = BrowserURL('profilpage') & AsyncLoad

            obj_subscriber = Async('details') & Format('%s %s',
                                CleanText('//div[text() = "nom :"]/following-sibling::div'),
                                CleanText(u'//div[contains(text(), "prénom")]/following-sibling::div'))
            obj_label = Env('id')
            obj_id = Env('id')

            def parse(self, el):
                self.env['id'] = re.sub(r'[^\d\-\.]', '', el.xpath('(//li[@class="n1 menuUsage toHighlight"])[1]//a')[0].text)

    @method
    class get_documents(ListElement):
        item_xpath = '//ul[@class="liste fe_clearfix factures"]/li'

        class item(ItemElement):
            klass = Bill

            obj_id = Format('%s_%s', Env('subid'), CleanDecimal(CleanText('.//span[@class="date magic_gras magic_font13"]')))
            obj__url = Attr('.//span[@class="telecharger pdf"]/a', 'href', default=NotAvailable)
            obj_date = Date(CleanText('.//span[@class="date magic_gras magic_font13"]'))
            obj_format = u"pdf"
            obj_type = u"bill"
            obj_price = CleanDecimal('span[@class="montant"]', replace_dots=True)
            obj_currency = Regexp(CleanText('span[@class="montant"]'), '([^\s\d,])')
