# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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

from weboob.browser.pages import HTMLPage, LoggedPage, JsonPage, pagination
from weboob.browser.filters.standard import CleanText, CleanDecimal, Env, Format, TableCell, Regexp, Date
from weboob.browser.elements import ItemElement, DictElement, TableElement, method
from weboob.browser.filters.html import Attr
from weboob.browser.filters.json import Dict
from weboob.capabilities.bill import Bill, Subscription
from weboob.capabilities.base import NotAvailable


class LoginPage(JsonPage):
    def is_logged(self):
        if "200" in Dict().filter(self.doc)['errorCode']:
            return True
        return False


class ProfilPage(LoggedPage, JsonPage):
    @method
    class get_list(DictElement):
        item_xpath = 'customerAccordContracts'

        class item(ItemElement):
            klass = Subscription

            obj_subscriber = Format('%s %s', Dict('bp/identity/firstName'), Dict('bp/identity/lastName'))
            obj_id = Dict('number')
            obj_label = obj_id


class DocumentsPage(LoggedPage, HTMLPage):
    @pagination
    @method
    class get_documents(TableElement):
        item_xpath = '//div[@class="factures"]//table/tbody/tr'
        head_xpath = '//div[@class="factures"]//table/thead/tr/th'

        col_date = u'Consulter ma facture détaillée'
        col_price = u'Montant (TTC)'

        def next_page(self):
            next_page = Attr('//ul[@class="years"]//span/../following-sibling::li/a', 'href')(self)
            if next_page:
                return next_page

        class item(ItemElement):
            klass = Bill

            obj_id = Format('%s_%s', Env('subid'), Env('docid'))
            obj__url = Env('url')
            obj_date = Date(Regexp(CleanText(TableCell('date')), ' ([\d\/]+)'))
            obj_format = u"pdf"
            obj_label = Format('Facture %s', Env('docid'))
            obj_type = u"bill"
            obj_price = CleanDecimal(TableCell('price'), replace_dots=True, default=NotAvailable)
            obj_currency = u"€"

            def parse(self, el):
                self.env['docid'] = Regexp(Attr('./td/a[@class="pdf"]', 'title'), '([\d]+)')(self)
                self.env['url'] = re.sub('[\t\r\n]', '', Attr('./td/a[@class="pdf"]', 'href')(self))
