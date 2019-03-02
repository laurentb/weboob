# -*- coding: utf-8 -*-

# Copyright(C) 2017      Baptiste Delpey
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


import re

from weboob.browser.pages import LoggedPage, HTMLPage, pagination
from weboob.browser.elements import TableElement, ItemElement, method
from weboob.browser.filters.html import Link, Attr, TableCell
from weboob.browser.filters.standard import CleanText, CleanDecimal, Regexp, \
                                            Format, Currency
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.bank import Account, Investment


class PreMandate(LoggedPage, HTMLPage):
    def on_load(self):
        form = self.get_form()
        form.submit()


class PreMandateBis(LoggedPage, HTMLPage):
    def on_load(self):
        link = re.match("document.location.href = '([^']+)';$", CleanText(u'//script')(self.doc)).group(1)
        self.browser.location(link)


class MandateAccountsList(LoggedPage, HTMLPage):
    @method
    class iter_accounts(TableElement):
        item_xpath = '//table[@id="accounts"]/tbody/tr'
        head_xpath = '//table[@id="accounts"]/thead/tr/th/a'

        col_id = re.compile(u'N° de compte')
        col_name = 'Nom'
        col_type = 'Type'
        col_valorisation = 'Valorisation'
        col_perf = re.compile('Perf')

        class Item(ItemElement):
            TYPES = {'CIFO':            Account.TYPE_MARKET,
                     'PEA':             Account.TYPE_PEA,
                     'Excelis VIE':     Account.TYPE_LIFE_INSURANCE,
                     'Satinium':        Account.TYPE_LIFE_INSURANCE,
                     'Satinium CAPI':   Account.TYPE_LIFE_INSURANCE,
                     'Excelis CAPI':    Account.TYPE_LIFE_INSURANCE,
                    }

            klass = Account

            obj_id = CleanText(TableCell('id'))
            obj_label = Format('%s %s', CleanText(TableCell('type')), CleanText(TableCell('name')))
            obj_currency = Currency(TableCell('valorisation'))
            obj_bank_name = u'La Banque postale'
            obj_balance = CleanDecimal(TableCell('valorisation'), replace_dots=True)
            obj_url = Link(TableCell('id'))
            obj_iban = NotAvailable

            def obj_url(self):
                td = TableCell('id')(self)[0]
                return Link(td.xpath('./a'))(self)

            def obj_type(self):
                return self.TYPES.get(CleanText(TableCell('type'))(self), Account.TYPE_UNKNOWN)


class Myiter_investments(TableElement):
    col_isin = 'Code ISIN'
    col_label = u'Libellé'
    col_unitvalue = u'Cours'
    col_valuation = 'Valorisation'


class MyInvestItem(ItemElement):
    klass = Investment

    obj_code = CleanText(TableCell('isin'))
    obj_label = CleanText(TableCell('label'))
    obj_quantity = CleanDecimal(TableCell('quantity'), replace_dots=True)
    obj_unitvalue = CleanDecimal(TableCell('unitvalue'), replace_dots=True)
    obj_valuation = CleanDecimal(TableCell('valuation'), replace_dots=True)


class MandateLife(LoggedPage, HTMLPage):
    @pagination
    @method
    class iter_investments(Myiter_investments):
        item_xpath = '//table[@id="asvSupportList"]/tbody/tr[count(td)>=5]'
        head_xpath = '//table[@id="asvSupportList"]/thead/tr/th'

        next_page = Regexp(Attr('//div[@id="turn_next"]/a', 'onclick'), 'href: "([^"]+)"')

        col_quantity = u'Quantité'

        class Item(MyInvestItem):
            pass


class MandateMarket(LoggedPage, HTMLPage):
    @method
    class iter_investments(Myiter_investments):
        # FIXME table was empty
        item_xpath = '//table[@id="valuation"]/tbody/tr[count(td)>=9]'
        head_xpath = '//table[@id="valuation"]/thead/tr/th'

        col_quantity = u'Qté'
        col_unitprice = u'Prix moyen'
        col_share = u'Poids'

        class Item(MyInvestItem):
            obj_unitprice = CleanDecimal(TableCell('unitprice'), replace_dots=True)
