# -*- coding: utf-8 -*-

# Copyright(C) 2015      Baptiste Delpey
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
from datetime import date
from dateutil.relativedelta import relativedelta

from weboob.browser.pages import HTMLPage, LoggedPage, pagination
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import CleanText
from weboob.browser.filters.html import Link
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction

__all__ = ['LoginPage', 'ErrorPage', 'AccountsPage', 'TransactionsPage']


class LoginPage(HTMLPage):
    def login(self, type, username, password):
        form = self.get_form(name='connecterForm')
        form['type'] = type
        form['login'] = username
        form['pwd'] = password
        form.url = '/ce_internet_public/seConnecter.event.do'
        form.submit()


class AccountsPage(LoggedPage, HTMLPage):
    @pagination
    @method
    class iter_accounts(ListElement):
        item_xpath = '//table[@id="ContentTable_datas"]//tr[@class]'

        next_page = Link('//table[@id="tgDecorationFoot"]//b/following-sibling::a[1]')

        class item(ItemElement):
            klass = Account

            obj_id = CleanText('./td[2]', replace=[(' ', '')])
            obj_label = CleanText('./td[1]')
            obj_type = Account.TYPE_CARD

    def get_link(self, account_id):
        return self.doc.xpath('.//a[replace(@title, " ", "")="%s"]' % account_id)[0].get("href")

    def expand(self):
        submit = '//input[contains(@value, "Display")]'
        form = self.get_form(submit=submit)
        node_checked = ''
        for item in self.doc.xpath('//input[contains(@id,"tree_id_checkbox")]'):
            node_checked += item.name.split('box_')[1] + '--'
        form['tree_idtreeviewNodeChecked'] = node_checked
        form['tree_idtreeviewNodeId'] = "0"
        form['fldParam_datas'] = "1"
        if 'Histo' in self.url:
            form['periodeDeb'] = (date.today() - relativedelta(months=6)).strftime("%d/%m/%Y")
            form['periodeFin'] = self.doc.xpath('//select[@name="periodeSaisie"]/option[@selected]/text()')[0]
            form['periodeSelectionMode'] = "input"
        onclick = self.doc.xpath(submit)[0].get("onclick")
        url_parts = re.findall("'([^']*)'", onclick)
        form.url = 'operation%s%sCorporate.event.do' % (url_parts[1], url_parts[0].title())
        form.submit()


class TransactionsPage(LoggedPage, HTMLPage):
    @pagination
    @method
    class get_history(ListElement):
        item_xpath = '//table[@id="ContentTable_datas"]//tr[@class]'

        next_page = Link('//table[@id="tgDecorationFoot"]//b/following-sibling::a[1]')

        class item(ItemElement):
            klass = FrenchTransaction

            obj_rdate = FrenchTransaction.Date(CleanText('./td[1]'))
            obj_date = FrenchTransaction.Date(CleanText('./td[3]'))
            obj_raw = FrenchTransaction.Raw(CleanText('./td[2]'))
            obj_amount = FrenchTransaction.Amount(CleanText('./td[5]'), replace_dots=False)
            obj_original_amount = FrenchTransaction.Amount(CleanText('./td[4]'), replace_dots=False)
            obj_original_currency = FrenchTransaction.Currency(CleanText('./td[4]'))
            obj_commission = FrenchTransaction.Amount(CleanText('./td[6]'), replace_dots=False)

    def is_not_sorted(self):
        return len(self.doc.xpath('//table[@id="ContentTable_datas"]/thead/tr/th[1]//img[contains(@src, "tri_bas_on")]')) == 0

    def sort(self):
        form = self.get_form(nr=0)
        form.url += '?sortDescriptor_datas=true'
        form['indexSort_datas'] = 1
        form['sort_datas'] = 'down'
        form.submit()

class ErrorPage(HTMLPage):
    pass
