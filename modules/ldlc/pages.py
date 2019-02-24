# -*- coding: utf-8 -*-

# Copyright(C) 2015      Vincent Paredes
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.filters.standard import CleanDecimal, CleanText, Env, Format, QueryValue, TableCell, Currency
from weboob.browser.elements import ListElement, ItemElement, method, TableElement
from weboob.browser.filters.html import Attr
from weboob.capabilities.bill import Bill, Subscription
from weboob.tools.date import parse_french_date


class HiddenFieldPage(HTMLPage):
    def get_ctl00_actScriptManager_HiddenField(self):
        param = QueryValue(Attr('//script[contains(@src, "js/CombineScriptsHandler.ashx?")]', 'src'), "_TSM_CombinedScripts_")(self.doc)
        return param


class HomePage(LoggedPage, HTMLPage):
    @method
    class get_list(ListElement):
        item_xpath = '//div[@id="divAccueilInformationClient"]//div[@id="divInformationClient"]'
        class item(ItemElement):
            klass = Subscription

            obj_subscriber = CleanText('.//div[@id="divlblTitleFirstNameLastName"]//span')
            obj_id = CleanText('.//span[2]')
            obj_label = CleanText('.//div[@id="divlblTitleFirstNameLastName"]//span')


class LoginPage(HiddenFieldPage):
    def login(self, username, password, website):
        form = self.get_form(id='aspnetForm')
        if website == 'part':
            form["ctl00$ctl00$cphMainContent$cphMainContent$txbMail"] = username
            form["ctl00$ctl00$cphMainContent$cphMainContent$txbPassword"] = password
            form["__EVENTTARGET"] = "ctl00$ctl00$cphMainContent$cphMainContent$butConnexion"
            form["ctl00_ctl00_actScriptManager_HiddenField"] = self.get_ctl00_actScriptManager_HiddenField()
        else:
            form["ctl00$cphMainContent$txbMail"] = username
            form["ctl00$cphMainContent$txbPassword"] = password
            form["__EVENTTARGET"] = "ctl00$cphMainContent$butConnexion"
            form["ctl00_ctl00_actScriptManager_HiddenField"] = self.get_ctl00_actScriptManager_HiddenField()
        form.submit()

    def get_error(self):
        return CleanText('//span[contains(text(), "Identifiants incorrects")]')(self.doc)


class BillsPage(LoggedPage, HiddenFieldPage):
    def get_range(self):
        for value in self.doc.xpath('//div[@class="commandListing content clearfix"]//select/option/@value'):
            yield value


class ParBillsPage(BillsPage):
    @method
    class iter_documents(TableElement):
        ignore_duplicate = True
        item_xpath = '//table[@id="TopListing"]/tr[position()>1]'
        head_xpath = '//table[@id="TopListing"]/tr[@class="TopListingHeader"]/td'

        col_id = 'N° de commande'
        col_date = 'Date'
        col_price = 'Montant TTC'

        class item(ItemElement):
            klass = Bill

            obj_id = Format('%s_%s', Env('subid'), CleanText(TableCell('id')))
            obj_url = Attr('./td[@class="center" or @class="center pdf"]/a', 'href')
            obj_format = 'pdf'
            obj_price = CleanDecimal(TableCell('price'), replace_dots=True)
            obj_currency = Currency(TableCell('price'))

            def obj_date(self):
                return parse_french_date(CleanText(TableCell('date'))(self)).date()

            def condition(self):
                return CleanText().filter(self.el.xpath('.//td')[-1]) != "" and len(self.el.xpath('./td[@class="center" or @class="center pdf"]/a/@href')) == 1


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
