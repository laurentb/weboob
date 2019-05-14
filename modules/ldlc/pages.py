# -*- coding: utf-8 -*-

# Copyright(C) 2015      Vincent Paredes
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

from weboob.browser.pages import HTMLPage, LoggedPage, PartialHTMLPage
from weboob.browser.filters.standard import (
    CleanDecimal, CleanText, Env, Format, QueryValue, TableCell, Currency, Regexp, Async, Date, Field,
)
from weboob.browser.elements import ListElement, ItemElement, method, TableElement
from weboob.browser.filters.html import Attr, Link
from weboob.capabilities import NotAvailable
from weboob.capabilities.bill import Bill, Subscription, DocumentTypes
from weboob.tools.date import parse_french_date
from .materielnet_pages import MyAsyncLoad


class HiddenFieldPage(HTMLPage):
    def get_ctl00_actScriptManager_HiddenField(self):
        param = QueryValue(Attr('//script[contains(@src, "js/CombineScriptsHandler.ashx?")]', 'src'), "_TSM_CombinedScripts_")(self.doc)
        return param


class HomePage(LoggedPage, HTMLPage):
    @method
    class get_subscriptions(ListElement):
        item_xpath = '//div[@id="divAccueilInformationClient"]//div[@id="divInformationClient"]'
        class item(ItemElement):
            klass = Subscription

            obj_subscriber = CleanText('.//div[@id="divlblTitleFirstNameLastName"]//span')
            obj_id = CleanText('.//span[2]')
            obj_label = CleanText('.//div[@id="divlblTitleFirstNameLastName"]//span')


class LoginPage(HTMLPage):
    def login(self, username, password):
        form = self.get_form(xpath='//form[contains(@action, "/Login/Login")]')
        form['Email'] = username
        form['Password'] = password
        form.submit()

    def get_error(self):
        return CleanText('//span[contains(text(), "Identifiants incorrects")]')(self.doc)


class DocumentsPage(LoggedPage, PartialHTMLPage):
    @method
    class get_documents(ListElement):
        item_xpath = '//div[@class="dsp-row"]'

        class item(ItemElement):
            klass = Bill

            load_details = Link('.//a[contains(text(), "détails")]') & MyAsyncLoad

            obj_id = Format('%s_%s', Env('subid'), Field('label'))
            obj_url = Async('details') & Link('//a[span[contains(text(), "Télécharger la facture")]]', default=NotAvailable)
            obj_date = Date(CleanText('./div[contains(@class, "cell-date")]'), dayfirst=True)
            obj_format = 'pdf'
            obj_label = Regexp(CleanText('./div[contains(@class, "cell-nb-order")]'), r' (.*)')
            obj_type = DocumentTypes.BILL
            obj_price = CleanDecimal(CleanText('./div[contains(@class, "cell-value")]'), replace_dots=(' ', '€'))
            obj_currency = 'EUR'


class BillsPage(LoggedPage, HiddenFieldPage):
    def get_range(self):
        for value in self.doc.xpath('//div[@class="commandListing content clearfix"]//select/option/@value'):
            yield value


class ProBillsPage(BillsPage):
    def get_view_state(self):
        return Attr('//input[@id="__VIEWSTATE"]', 'value')(self.doc)

    @method
    class iter_documents(TableElement):
        ignore_duplicate = True
        item_xpath = '//table[@id="TopListing"]/tr[contains(@class, "rowTable")]'
        head_xpath = '//table[@id="TopListing"]/tr[@class="headTable"]/td'

        col_id = 'N° de commande'
        col_date = 'Date'
        col_price = 'Montant HT'

        class item(ItemElement):
            klass = Bill

            obj_id = Format('%s_%s', Env('subid'), CleanText(TableCell('id')))
            obj_url = '/Account/CommandListingPage.aspx'
            obj_format = 'pdf'
            obj_price = CleanDecimal(TableCell('price'), replace_dots=True)
            obj_currency = Currency(TableCell('price'))

            def obj_date(self):
                return parse_french_date(CleanText(TableCell('date'))(self)).date()
