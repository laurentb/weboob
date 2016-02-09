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
from weboob.browser.filters.standard import CleanDecimal, CleanText, Env, Format, Date
from weboob.browser.filters.html import Attr
from weboob.capabilities.bill import Bill


class BillsPage(HTMLPage):
    @method
    class get_list(ListElement):
        class item(ItemElement):
            klass = Subscription

            obj_label = CleanText('(//li[@class="n1 menuUsage toHighlight"])[1]')
            obj_subscriber = CleanText('//div[@class="blocCompte blocPrincipal"]//h2/a')
            obj_id = Env('id')

            def parse(self, el):
                self.env['id'] = re.sub(r'[^\d\-\.]', '', el.xpath('(//li[@class="n1 menuUsage toHighlight"])[1]//a')[0].text)

    @method
    class get_documents(ListElement):
        item_xpath = '//ul[@class="liste fe_clearfix factures"]/li'

        class item(ItemElement):
            klass = Bill

            obj__url = Attr('.//span[@class="telecharger pdf"]/a', 'href')
            obj_id = Format('%s.%s', Env('subid'), CleanDecimal(CleanText('.//span[@class="date magic_gras magic_font13"]')))
            obj_date = Date(CleanText('.//span[@class="date magic_gras magic_font13"]'))
            obj_format = u"pdf"
            obj_type = u"bill"
            obj_price = CleanDecimal('span[@class="montant"]', replace_dots=True)

