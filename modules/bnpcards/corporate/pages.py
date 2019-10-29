# -*- coding: utf-8 -*-

# Copyright(C) 2015      Baptiste Delpey
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
from datetime import date
from dateutil.relativedelta import relativedelta

from weboob.browser.pages import HTMLPage, LoggedPage, pagination, NextPage
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import CleanText, CleanDecimal, Field, Format, Env
from weboob.browser.filters.html import Link, Attr
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction

__all__ = ['LoginPage', 'ErrorPage', 'AccountsPage', 'TransactionsPage']


class LoginPage(HTMLPage):
    def login(self, username, password):
        form = self.get_form(name='connecterForm')
        form['type'] = '2'  # Gestionnaire
        form['login'] = username
        form['pwd'] = password[:8]
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

            obj_id = Format('%s%s%s', CleanText('./td[2]', replace=[(' ', '')]), CleanText('./td[3]'),
                            CleanText('./td[1]', replace=[(' ', '')]))

            obj__owner = CleanText('./td[1]')
            obj_number = CleanText('./td[2]', replace=[(' ', '')])
            obj_label = CleanText('./td[1]')
            obj_type = Account.TYPE_CARD
            obj__status = CleanText('./td[5]')
            obj_currency = 'EUR'
            obj_url = Link('./td[2]/a')
            obj__company = Env('company', default=None)  # this field is something used to make the module work, not something meant to be displayed to end users

    @pagination
    def get_link(self, account_id, owner):
        for tr in self.doc.xpath('//tr'):
            link = tr.xpath('.//a[replace(@title, " ", "") = $id]/@href', id=account_id)
            if not link:
                continue
            if CleanText('.//td[1]')(tr) != owner:
                continue
            yield link[0]
            return
        else:
            next_page = self.doc.xpath('//table[@id="tgDecorationFoot"]//b/following-sibling::a[1]/@href')
            if next_page:
                raise NextPage(next_page[0])

    def expand(self):
        submit = '//input[contains(@value, "Display")]'
        form = self.get_form(submit=submit)
        node_checked = ''
        for item in self.doc.xpath('//input[contains(@id,"tree_id_checkbox")]'):
            node_checked += item.name.split('box_')[1] + '--'
        form['tree_idtreeviewNodeChecked'] = node_checked
        form['tree_idtreeviewNodeId'] = "0"
        form['fldParam_datas'] = "1"
        form['statutSelectionne'] = "100"
        if 'Histo' in self.url:
            form['periodeDeb'] = (date.today() - relativedelta(months=6)).strftime("%d/%m/%Y")
            form['periodeFin'] = (date.today() + relativedelta(months=4)).strftime("%d/%m/%Y")
            form['periodeSelectionMode'] = "input"
        onclick = self.doc.xpath(submit)[0].get("onclick")
        url_parts = re.findall(r"'([^']*)'", onclick)
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
            _obj_amnt = FrenchTransaction.Amount(CleanText('./td[5]'), replace_dots=False)
            obj_original_amount = FrenchTransaction.Amount(CleanText('./td[4]'), replace_dots=False)
            obj_original_currency = FrenchTransaction.Currency(CleanText('./td[4]'))
            obj_commission = FrenchTransaction.Amount(CleanText('./td[6]'), replace_dots=False)

            def obj__coming(self):
                if Field('date')(self) >= date.today():
                    return True
                return

            def obj_amount(self):
                if not Field('obj_commission'):
                    return Field('_obj_amnt')
                else:
                    return CleanDecimal(replace_dots=False).filter(self.el.xpath('./td[5]')) - CleanDecimal(replace_dots=False).filter(self.el.xpath('./td[6]'))

    def is_not_sorted(self, order='down'):
        translate = {'down': 'bas', 'up': 'haut'}
        return len(self.doc.xpath('//table[@id="ContentTable_datas"]/thead/tr/th[1]//img[contains(@src, "tri_%s_on")]' % translate[order])) == 0

    def sort(self, order='down'):
        form = self.get_form(nr=0)
        form.url += '?sortDescriptor_datas=true'
        form['indexSort_datas'] = 3
        form['sort_datas'] = order
        form.submit()

    def assert_first_page_or_go_there(self):
        if len(self.doc.xpath('//table[@id="tgDecorationFoot"]')) and not len(self.doc.xpath('//table[@id="tgDecorationFoot"]//b[contains(text(), "1")]')):
            url = Attr('//table[@id="tgDecorationFoot"]//a[contains(text(), "1")]', 'href', default=None)(self.doc)
            if url is None:
                # at page=4, there is "<Première page> ... <2> <3> 4"
                url = Attr('//table[@id="tgDecorationFoot"]//a[contains(text(), "Première page")]', 'href')(self.doc)
            self.browser.location(url)


class ErrorPage(HTMLPage):
    pass
