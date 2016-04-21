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


from weboob.browser.pages import HTMLPage, LoggedPage, pagination
from weboob.browser.elements import ListElement, ItemElement, SkipItem, method, TableElement
from weboob.browser.filters.standard import CleanText, Upper, Capitalize, Date, Regexp, CleanDecimal, Env, TableCell
from weboob.browser.filters.html import Attr
from weboob.capabilities.bank import Account, Investment, Transaction
from weboob.capabilities.base import NotLoaded


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotLoaded)
    return CleanDecimal(*args, **kwargs)


class LoginPage(HTMLPage):
    def login(self, login, password):
        form = self.get_form(name="bloc_ident")
        form['_cm_user'] = login
        form['_cm_pwd'] = password
        form.submit()


class AccountsPage(LoggedPage, HTMLPage):
    def get_investment_link(self):
        return Attr(None, 'href').filter(self.doc.xpath('//a[contains(text(), "fonds")]'))

    @method
    class iter_accounts(ListElement):
        class item(ItemElement):
            klass = Account

            obj_id = Regexp(Upper('//table[@class="fiche"]//td'), '[\s]+([^\s]+)[\s]+([^\s]+).*:[\s]+([^\s]+)', '\\1\\2\\3')
            obj_type = Account.TYPE_PEE
            obj_label = Regexp(Capitalize('//h1'), 'Compte[\s]+(.*)', default=u"Épargne Salariale")
            obj_balance = MyDecimal('//td[em[contains(text(), "Total")]]/following-sibling::td')


class InvestmentPage(LoggedPage, HTMLPage):
    @method
    class iter_investment(ListElement):
        item_xpath = '//table[@class="liste"]/tbody//tr[td[contains(text(), "total")]]'

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText('./preceding-sibling::tr[td[6]][1]/td[1]')
            obj_quantity = CleanDecimal('./td[position() = (last()-1)]')
            obj_unitvalue = MyDecimal('./preceding-sibling::tr[td[6]][1]/td[3]')
            obj_valuation = MyDecimal('./td[position() = last()]')
            obj_vdate = Date(Regexp(CleanText(u'//p[contains(text(), "financière au ")]'), 'au[\s]+(.*)'))


class HistoryPage(LoggedPage, HTMLPage):
    DEBIT_WORDS = ['retrait', 'sortant', 'frais']

    @pagination
    @method
    class iter_history(TableElement):
        item_xpath = '//table[@class="liste"]/tbody/tr'
        head_xpath = '//table[@class="liste"]/thead/tr/th'

        col_date = 'Date'

        def next_page(self):
            next_page = self.el.xpath('//a[contains(@href, "Suiv")]/@href')
            if next_page:
                return next_page[0]

        class item(ItemElement):
            klass = Transaction

            obj_date = Date(CleanText(TableCell('date')))
            obj_type = Transaction.TYPE_BANK
            obj_label = Env('label')
            obj_amount = Env('amount')
            obj_investments = Env('investments')

            def parse(self, el):
                link = el.xpath('.//a[1]')[0].get('href', '')
                doc = self.page.browser.open(link).page.doc

                if not CleanText('//table/tbody/tr[not(td[9])]')(doc):
                    self.page.browser.skipped.append(doc)
                    raise SkipItem()

                label = CleanText('.//a[1]')(self)
                amount = MyDecimal('//table/tbody/tr[not(td[9])]/td[4]')(doc)

                if any(word in label.lower() for word in self.page.DEBIT_WORDS):
                    amount = -amount

                self.env['label'] = label
                self.env['amount'] = amount

                investments = []
                for tr in doc.xpath('//table/tbody/tr[td[9]]'):
                    i = Investment()
                    i.label = CleanText().filter(tr.xpath('./td[3]'))
                    i.quantity = MyDecimal().filter(tr.xpath('./td[5]'))
                    i.unitvalue = MyDecimal().filter(tr.xpath('./td[4]'))
                    i.valuation = MyDecimal().filter(tr.xpath('./td[6]'))
                    i.vdate = Date(Regexp(CleanText(u'//p[contains(text(), " du ")]'), 'du[\s]+(.*)'))(doc)
                    investments.append(i)
                self.env['investments'] = investments

    def iter_history_skipped(self):
        for doc in self.browser.skipped:
            for tr in doc.xpath('//table/tbody/tr'):
                t = Transaction()
                t.date = Date(Regexp(CleanText(u'//p[contains(text(), " du ")]'), 'du[\s]+(.*)'))(doc)
                t.type = Transaction.TYPE_BANK
                t.label = CleanText().filter(tr.xpath('./td[1]'))
                t.amount = MyDecimal().filter(tr.xpath('./td[6]'))

                if any(word in t.label.lower() for word in self.DEBIT_WORDS):
                    t.amount = -t.amount

                i = Investment()
                i.label = CleanText().filter(tr.xpath('./td[3]'))
                i.quantity = MyDecimal().filter(tr.xpath('./td[5]'))
                i.unitvalue = MyDecimal().filter(tr.xpath('./td[4]'))
                i.valuation = MyDecimal().filter(tr.xpath('./td[6]'))
                i.vdate = Date(Regexp(CleanText(u'//p[contains(text(), " du ")]'), 'du[\s]+(.*)'))(doc)
                t.investments = [i]

                yield t
