# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.filters.standard import CleanText, CleanDecimal, Env, Format, Date
from weboob.browser.filters.html import Attr, TableCell
from weboob.browser.elements import ListElement, ItemElement, TableElement, method
from weboob.capabilities.bill import DocumentTypes, Bill, Document, Subscription
from weboob.capabilities.base import NotAvailable


class LoginPage(HTMLPage):
    def login(self, login, password):
        form = self.get_form('//form[contains(@action, "/login_check")]')
        form['_username'] = login
        form['_password'] = password
        form.submit()


class ProfilPage(LoggedPage, HTMLPage):
    @method
    class get_list(ListElement):
        class item(ItemElement):
            klass = Subscription

            obj_subscriber = Format(
                    '%s %s',
                    CleanText('//label[@for="form_firstname"]/../following-sibling::div'),
                    CleanText('//label[@for="form_firstname"]/../following-sibling::div')
            )
            obj_id = Env('username')
            obj_label = obj_id

            def parse(self, el):
                self.env['username'] = self.page.browser.username


class DocumentsPage(LoggedPage, HTMLPage):
    @method
    class get_bills(TableElement):
        item_xpath = '//h3[contains(text(), "bills")]/following-sibling::table//tr[position() > 1]'
        head_xpath = '//h3[contains(text(), "bills")]/following-sibling::table//tr/th'

        col_id = 'Id'
        col_date = 'Date'
        col_price = 'Total TTC'

        class item(ItemElement):
            klass = Bill

            obj_id = Format('%s_%s', Env('username'), CleanDecimal(TableCell('id')))
            obj__url = Attr('.//a[contains(text(), "PDF")]', 'href', default=NotAvailable)
            obj_date = Date(CleanText(TableCell('date')))
            obj_format = 'pdf'
            obj_label = Format('Facture %s', CleanDecimal(TableCell('id')))
            obj_type = DocumentTypes.BILL
            obj_price = CleanDecimal(TableCell('price'))
            obj_currency = 'EUR'

            def condition(self):
                return CleanText(TableCell('id'))(self) != "No bills"

            def parse(self, el):
                self.env['username'] = self.page.browser.username

    @method
    class get_documents(ListElement):
        item_xpath = '//a[contains(@href, ".pdf")]'

        class item(ItemElement):
            klass = Document

            obj_id = Format('%s_%s', Env('username'), Env('docid'))
            obj__url = Attr('.', 'href')
            obj_format = 'pdf'
            obj_label = CleanText('.')
            obj_type = DocumentTypes.OTHER

            def parse(self, el):
                self.env['username'] = self.page.browser.username
                self.env['docid'] = re.sub('[^a-zA-Z0-9-_*.]', '', CleanText('.')(self))
