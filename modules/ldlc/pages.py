# -*- coding: utf-8 -*-

# Copyright(C) 2015      Vincent Paredes
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

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.filters.standard import CleanDecimal, CleanText, Env, Format, QueryValue
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.html import Attr
from weboob.capabilities.bill import Bill, Subscription
from weboob.tools.date import parse_french_date

class HomePage(LoggedPage, HTMLPage):
    @method
    class get_list(ListElement):
        item_xpath = '//div[@id="divAccueilInformationClient"]//div[@id="divInformationClient"]'
        class item(ItemElement):
            klass = Subscription

            obj_subscriber = CleanText('.//div[@id="divlblTitleFirstNameLastName"]//span')
            obj_id = CleanText('.//span[2]')
            obj_label = CleanText('.//div[@id="divlblTitleFirstNameLastName"]//span')


class LoginPage(HTMLPage):
    def login(self, username, password):
        form = self.get_form(xpath='//form[@id="aspnetForm"]')
        form["ctl00$ctl00$cphMainContent$cphMainContent$txbMail"] = username
        form["ctl00$ctl00$cphMainContent$cphMainContent$txbPassword"] = password
        form["__EVENTTARGET"] = "ctl00$ctl00$cphMainContent$cphMainContent$butConnexion"
        form["ctl00_ctl00_actScriptManager_HiddenField"] = self.get_ctl00_actScriptManager_HiddenField()
        form.submit()

    def get_ctl00_actScriptManager_HiddenField(self):
        param = QueryValue(Attr('//script[contains(@src, "js/CombineScriptsHandler.ashx?")]', 'src'), "_TSM_CombinedScripts_")(self.doc)
        return param


class BillsPage(LoggedPage, HTMLPage):
    def get_range(self):
        for value in self.doc.xpath('//div[@class="commandListing content clearfix"]//select/option/@value'):
            yield value

    @method
    class get_documents(ListElement):
        item_xpath = '//table[@id="TopListing"]//tr'

        class item(ItemElement):
            klass = Bill

            obj_id = Format('%s_%s', Env('subid'), CleanText('./td[3]'))
            obj_url = Attr('./td[@class="center" or @class="center pdf"]/a', 'href')
            obj_date = Env('date')
            obj_format = u"pdf"
            obj_type = u"bill"
            obj_price = CleanDecimal('./td[@class="center montant"]/span', replace_dots=True)

            def parse(self, el):
                self.env['date'] = parse_french_date(el.xpath('./td[2]')[0].text).date()

            def condition(self):
                return CleanText().filter(self.el.xpath('.//td')[-1]) != "" and len(self.el.xpath('./td[@class="center" or @class="center pdf"]/a/@href')) == 1
