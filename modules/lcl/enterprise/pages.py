# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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


import re, requests

from weboob.browser.pages import HTMLPage, LoggedPage, pagination
from weboob.browser.elements import ListElement, ItemElement, TableElement, method
from weboob.browser.filters.standard import CleanText, Date, CleanDecimal, Env
from weboob.browser.filters.html import Link, TableCell
from weboob.capabilities.bank import Account
from weboob.capabilities.profile import Profile
from weboob.capabilities.base import NotAvailable
from weboob.exceptions import BrowserPasswordExpired

from ..pages import Transaction


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)


class LoginPage(HTMLPage):
    def get_error(self):
        return CleanText(default=False).filter(self.doc.xpath('//li[contains(@class, "erreur")]'))

    def login(self, login, password):
        form = self.get_form(id="myForm")
        form['login'] = login
        form['pwd'] = password
        form['mode'] = '1'
        form.submit()


class MovementsPage(LoggedPage, HTMLPage):
    def get_changecompte(self, link):
        form = self.get_form('//form[contains(@action, "changeCompte")]')
        m = re.search('\'(\d+).*\'(\d+)', link)
        form['perimetreMandatParentData'] = m.group(1)
        form['perimetreMandatEnfantData'] = m.group(2)
        # Can't do multi with async because of inconsistency...
        return self.browser.open(form.url, data=dict(form)).page, form.url, dict(form)

    @method
    class iter_accounts(ListElement):
        def parse(self, el):
            # multi accounts separated in multiple companies
            self.item_xpath = '//form[contains(@action, "changeCompte")]//ul[@class="listeEnfants"]/li/a'
            self.env['multi'] = bool(self.page.doc.xpath(self.item_xpath))
            if self.env['multi']:
                return

            # simple multi accounts
            self.item_xpath = '//form[contains(@action, "changeCompte")]//ul[@class="layerEnfants"]/li/a'
            self.env['multi'] = bool(self.page.doc.xpath(self.item_xpath))
            if self.env['multi']:
                return

            # single account
            self.item_xpath = '//*[@id="perimetreMandatEnfantLib"]'

        class item(ItemElement):
            klass = Account

            def obj_id(self):
                return CleanText('.')(self).strip().replace(' ', '').split('-')[0]

            def obj_label(self):
                return CleanText('.')(self).split("-")[-1].strip()

            obj_type = Account.TYPE_CHECKING

            obj_balance = Env('balance')
            obj_currency = Env('currency')
            obj__url = Env('url')
            obj__data = Env('data')

            def parse(self, el):
                page, url, data = self.page.get_changecompte(Link('.')(self)) if self.env['multi'] else (self.page, None, None)
                balance_xpath = '//div[contains(text(),"Solde")]/strong'
                self.env['balance'] = MyDecimal().filter(page.doc.xpath(balance_xpath))
                self.env['currency'] = Account.get_currency(CleanText().filter(page.doc.xpath(balance_xpath)))
                self.env['url'] = url
                self.env['data'] = data


    @pagination
    @method
    class iter_history(TableElement):
        item_xpath = '//table[@id="listeOperations" or @id="listeEffets"]/tbody/tr[td[5]]'
        head_xpath = '//table[@id="listeOperations"]/thead/tr/th'

        col_raw = re.compile(u'Libellé')
        col_debit = re.compile(u'Débit')
        col_credit = re.compile(u'Crédit')

        def next_page(self):
            url = Link('//a[contains(text(), "Page suivante")]', default=None)(self)
            if url:
                m = re.search('\s+\'([^\']+).*\'(\d+)', url)
                return requests.Request("POST", m.group(1), data={'numPage': m.group(2)})

        class item(ItemElement):
            klass = Transaction

            obj_raw = Transaction.Raw(TableCell('raw'))
            obj_date = Date(CleanText('./td[1]'), dayfirst=True)
            obj_vdate = Date(CleanText('./td[2]'), dayfirst=True)

            def obj_amount(self):
                credit = MyDecimal(TableCell('credit'))(self)
                debit = MyDecimal(TableCell('debit'))(self)
                return credit if credit else -debit


class ProfilePage(LoggedPage, HTMLPage):
    @method
    class get_profile(ItemElement):
        klass = Profile

        obj_name = CleanText('//div[@class="headerInfos"][not(@id)]/span')
        obj_phone = CleanText('//div[label[@id="tel_fix_label"]]/following-sibling::div[1]')
        obj_email = CleanText('//div[label[@id="email_label"]]/following-sibling::div[1]')


class PassExpiredPage(HTMLPage):
    def on_load(self):
        raise BrowserPasswordExpired("Renouvellement de mot de passe requis.")
