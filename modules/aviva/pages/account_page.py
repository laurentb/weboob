# -*- coding: utf-8 -*-

# Copyright(C) 2012-2019  Budget Insight
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

from weboob.browser.pages import LoggedPage
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import (
    CleanText, Field, Map, Regexp
)
from weboob.browser.filters.html import AbsoluteLink
from weboob.capabilities.bank import Account
from weboob.capabilities.base import NotAvailable

from .detail_pages import BasePage


ACCOUNT_TYPES = {
    'Assurance vie': Account.TYPE_LIFE_INSURANCE,
    'Epargne – Retraite': Account.TYPE_PERP,
}


class AccountsPage(LoggedPage, BasePage):
    @method
    class iter_accounts(ListElement):
        item_xpath = '//div[contains(@class, "o-product-roundels")]/div[@data-policy]'

        class item(ItemElement):
            klass = Account

            obj_id = CleanText('./@data-policy')
            obj_number = Field('id')
            obj_label = CleanText('.//p[has-class("a-heading")]', default=NotAvailable)
            obj_url = AbsoluteLink('.//a[contains(text(), "Détail")]')
            obj_type = Map(Regexp(CleanText('../../../div[contains(@class, "o-product-roundels-category")]'),
                           r'Vérifier votre (.*) contrats', default=NotAvailable),
                           ACCOUNT_TYPES, Account.TYPE_UNKNOWN)

            def condition(self):
                # 'Prévoyance' div is for insurance contracts -- they are not bank accounts and thus are skipped
                ignored_accounts = (
                    'Prévoyance', 'Responsabilité civile', 'Complémentaire santé', 'Protection juridique',
                    'Habitation', 'Automobile',
                )
                return CleanText('../../div[has-class("o-product-tab-category")]', default=NotAvailable)(self) not in ignored_accounts
