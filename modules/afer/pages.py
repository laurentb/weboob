# -*- coding: utf-8 -*-

# Copyright(C) 2015      James GALT
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

from random import randint

import requests

from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import CleanText, Regexp, CleanDecimal, Date, Async, BrowserURL
from weboob.browser.pages import HTMLPage, LoggedPage, pagination
from weboob.capabilities.bank import Account, Investment, Transaction
from weboob.capabilities.base import NotAvailable
from weboob.exceptions import BrowserUnavailable


class LoginPage(HTMLPage):
    def login(self, login, passwd):
        form = self.get_form(name='_DominoForm')
        form['Username'] = login
        form['password'] = passwd
        form.submit()

    def is_here(self):
        return bool(self.doc.xpath('//form[@name="_DominoForm"]'))


class IndexPage(LoggedPage, HTMLPage):
    def on_load(self):
        HTMLPage.on_load(self)

        # website sometime crash
        if self.doc.xpath(u'//div[@id="divError"]/span[contains(text(),"Une erreur est survenue")]'):
            raise BrowserUnavailable()

    def is_here(self):
        return bool(self.doc.xpath('//img[contains(@src, "deconnexion.jpg")]'))

    @method
    class iter_accounts(ListElement):
        item_xpath = '//div[@id="adhesions"]/table//tr[td//a]'

        class item(ItemElement):
            klass = Account

            obj_id = CleanText('.//a')
            obj_label = CleanText('.//td[3]')
            obj_currency = u'EUR'
            def obj_balance(self):
                if not '%' in CleanText('.//td[last()-2]')(self):
                    return CleanDecimal('.//td[last()-2]', replace_dots=True)(self)
                elif not '%' in CleanText('.//td[last()-3]')(self):
                    return CleanDecimal('.//td[last()-3]', replace_dots=True)(self)
                else:
                    return NotAvailable

            obj_type = Account.TYPE_LIFE_INSURANCE


class AccountDetailPage(LoggedPage, HTMLPage):
    def is_here(self):
        return bool(self.doc.xpath('//*[@id="linkadhesion"]/a'))

    @method
    class iter_investments(ListElement):
        item_xpath = '//div[@id="savingBalance"]/table[1]//tr'

        class item(ItemElement):
            def condition(self):
                return self.el.xpath('./td[contains(@class,"dateUC")]')

            klass = Investment
            obj_label = CleanText('.//td[1]')
            obj_code = NotAvailable
            obj_description = NotAvailable
            obj_quantity = CleanDecimal('.//td[7]', replace_dots=True, default=NotAvailable)
            obj_unitvalue = CleanDecimal('.//td[5]', replace_dots=True, default=NotAvailable)
            obj_valuation = CleanDecimal('.//td[3]', replace_dots=True)
            obj_vdate = Date(Regexp(CleanText('.//td[2]'), '(((0[1-9]|[12][0-9]|3[01])[- /.]'
                                                               '(0[13578]|1[02])|(0[1-9]|[12][0-9]|30)[- /.](0[469]|11)|'
                                                               '(0[1-9]|1\d|2[0-8])[- /.]02)[- /.]\d{4}|29[- /.]02[- /.]'
                                                               '(\d{2}(0[48]|[2468][048]|[13579][26])|([02468][048]|'
                                                               '[1359][26])00))$', nth=0), dayfirst=True)

            def obj_unitprice(self):
                try:
                    return CleanDecimal(replace_dots=True, default=NotAvailable).filter(
                            self.el.xpath('.//td[6]')[0].text) / \
                           CleanDecimal(replace_dots=True, default=NotAvailable).filter(
                                   self.el.xpath('.//td[7]')[0].text)
                except TypeError:
                    return NotAvailable

            def obj_diff(self):
                try:
                    return self.obj.valuation - (self.obj.unitprice * self.obj.quantity)
                except TypeError:
                    return NotAvailable


class AccountHistoryPage(LoggedPage, HTMLPage):
    @pagination
    @method
    class iter_history(ListElement):
        item_xpath = '//table[@class="confirmation-table"]//tr'

        def next_page(self):
            if self.page.doc.xpath("//table[@id='tabpage']//td"):
                array_page = self.page.doc.xpath("//table[@id='tabpage']//td")[0][3].text
                curr_page, max_page = array_page.split(' ')[1::2]
                if int(curr_page) < int(max_page):
                    data = self.env['data']
                    data['page'] += 1
                    data['al'] = randint(1, 1000)
                    return requests.Request("POST", self.page.url, data=data)
            return

        class item(ItemElement):
            condition = lambda self: len(self.el.xpath('./td')) >= 3
            def load_details(self):
                a = self.el.xpath(".//img[@src='../../images/commun/loupe.png']")
                if len(a) > 0:
                    values = a[0].get('onclick').replace('OpenDetailOperation(', '') \
                        .replace(')', '').replace(' ', '').replace("'", '').split(',')
                    keys = ["nummvt", "&numads", "dtmvt", "typmvt"]
                    data = dict(zip(keys, values))
                    url = BrowserURL('history_detail')(self)
                    r = self.page.browser.async_open(url=url, data=data)
                    return r
                return None

            klass = Transaction
            obj_date = obj_rdate = obj_vdate = Date(CleanText('.//td[3]'), dayfirst=True)
            obj_label = CleanText('.//td[1]')

            def obj_amount(self):
                am = CleanDecimal('.//td[2]', replace_dots=True, default=NotAvailable)(self)
                if am is not NotAvailable:
                    return am
                return (Async('details') & CleanDecimal('//div//tr[2]/td[2]', replace_dots=True, default=NotAvailable))(
                    self)


class BadLogin(HTMLPage):
    pass
