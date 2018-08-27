# -*- coding: utf-8 -*-

# Copyright(C) 2017 Édouard Lambert, David Kremer
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

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import (
    CleanText, Env, Field, Async, AsyncLoad, Currency
)
from weboob.browser.filters.html import AbsoluteLink
from weboob.capabilities.bank import Account
from weboob.capabilities.base import NotAvailable

from .detail_pages import InvestmentPage, BasePage


class AccountsPage(LoggedPage, BasePage, HTMLPage):
    TYPES = {
        'Assurance vie': Account.TYPE_LIFE_INSURANCE,
        'Epargne – Retraite': Account.TYPE_PERP,
    }

    @method
    class iter_accounts(ListElement):
        item_xpath = '//div[@class="o-product-tabs__tab"]/div[has-class("o-product-tabs__tab-content")]/div[@data-policy]'

        class item(ItemElement):
            klass = Account

            load_details = Field('_link') & AsyncLoad  # details on investment, balance, etc

            obj_id = CleanText('./@data-policy')
            obj_number = Field('id')
            obj_label = CleanText('.//p[has-class("a-heading")]', default=NotAvailable)
            obj_balance = Async('details') & InvestmentPage.balance_filter
            obj_valuation_diff = Async('details') & InvestmentPage.valuation_filter
            obj__link = AbsoluteLink(u'.//a[contains(text(), "Détail")]')
            obj_currency = Async('details') & Currency('//ul[has-class("m-data-group")]//strong')
            # Additional waranty : need to know what to do with this
            obj__additionalwaranty = Env('additionalwaranty')

            def condition(self):
                # 'Prévoyance' div is for insurance contracts -- they are not bank accounts and thus are skipped
                to_skip = ('Prévoyance', 'Responsabilité civile', 'Complémentaire santé', 'Protection juridique', 'Habitation')
                kind = CleanText('../../div[has-class("o-product-tab-category")]', default=NotAvailable)(self)
                return (kind not in to_skip)

            def obj_type(self):
                kind = CleanText('../../div[has-class("o-product-tab-category")]', default=NotAvailable)(self)
                return self.page.TYPES.get(kind, NotAvailable)

            def parse(self, el):
                additionalwaranty = []
                detail_page = self.page.browser.location(Field('_link')(self)).page
                for line in detail_page.doc.xpath(
                        u'//h2[contains(text(), "complémentaire")]/following-sibling::div//div[@class="line"]'
                ):
                    values = {}
                    values['label'] = CleanText().filter(line.xpath('./div[@data-label="Nom du support"]'))
                    values['amount'] = CleanText().filter(line.xpath('./div[@data-label="Montant total investi"]'))
                    additionalwaranty.append(values)
                self.env['additionalwaranty'] = additionalwaranty
