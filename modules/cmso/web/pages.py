# -*- coding: utf-8 -*-

# Copyright(C) 2014      smurail
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


import datetime

from weboob.browser.pages import HTMLPage, LoggedPage, pagination
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import CleanText, CleanDecimal, Regexp, DateGuesser, Env
from weboob.browser.filters.html import Link
from weboob.capabilities.bank import Account

from ..transaction import Transaction

__all__ = ['LoginPage']


class LoginPage(HTMLPage):
    def login(self, username, password):
        form = self.get_form('//form[@id="formAuth"]')

        form['noPersonne'] = username
        form['motDePasse'] = password

        form.submit()


class CmsoListElement(ListElement):
    item_xpath = '//table[@class="Tb" and tr[1][@class="LnTit"]]/tr[@class="LnA" or @class="LnB"]'


class AccountsPage(LoggedPage, HTMLPage):
    @method
    class iter_accounts(CmsoListElement):
        class item(ItemElement):
            klass = Account

            obj__history_url = Link('./td[1]/a')
            obj_label = CleanText('./td[1]')
            obj_id = obj__history_url & Regexp(pattern="indCptSelectionne=(\d+)") | None
            obj_balance = CleanDecimal('./td[2]', replace_dots=True)

            def validate(self, obj):
                if obj.id is None:
                    obj.id = obj.label.replace(' ', '')
                return True


class CmsoTransactionElement(ItemElement):
    klass = Transaction

    def condition(self):
        return len(self.el) >= 5 and not self.el.get('id', '').startswith('libelleLong')


class HistoryPage(LoggedPage, HTMLPage):
    def iter_history(self, *args, **kwargs):
        if self.doc.xpath('//a[@href="1-situationGlobaleProfessionnel.act"]'):
            return self.iter_history_rest_page(*args, **kwargs)
        return self.iter_history_first_page(*args, **kwargs)

    @method
    class iter_history_first_page(CmsoListElement):
        class item(CmsoTransactionElement):
            def validate(self, obj):
                return obj.date >= datetime.date.today().replace(day=1)

            def date(selector):
                return DateGuesser(CleanText(selector), Env('date_guesser')) | Transaction.Date(selector)

            obj_date = date('./td[1]')
            obj_vdate = date('./td[2]')
            # Each row is followed by a "long labelled" version
            obj_raw = Transaction.Raw('./following-sibling::tr[1][starts-with(@id, "libelleLong")]/td[3]')
            obj_amount = Transaction.Amount('./td[5]', './td[4]')

    @pagination
    @method
    class iter_history_rest_page(CmsoListElement):
        next_page = Link('//span[has-class("Rappel")]/following-sibling::*[1][@href]')

        class item(CmsoTransactionElement):
            obj_date = Transaction.Date('./td[2]')
            obj_vdate = Transaction.Date('./td[1]')
            obj_raw = Transaction.Raw('./td[3]')
            obj_amount = Transaction.Amount('./td[5]', './td[4]', replace_dots=False)
