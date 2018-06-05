# -*- coding: utf-8 -*-

# Copyright(C) 2017      Tony Malto
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

from __future__ import unicode_literals

import re

from weboob.browser.pages import FormNotFound, HTMLPage, LoggedPage, XMLPage
from weboob.browser.elements import ItemElement, method, ListElement, TableElement
from weboob.capabilities.bank import Account, Investment
from weboob.browser.filters.standard import (
    CleanText, CleanDecimal, Currency, Date, Eval, Field, Regexp,
)
from weboob.browser.filters.html import Attr, TableCell
from weboob.capabilities.base import NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


class Transaction(FrenchTransaction):
    PATTERNS = [
        (re.compile(r'Versement'), FrenchTransaction.TYPE_TRANSFER),
        (re.compile(r'Arbitrage'), FrenchTransaction.TYPE_ORDER)
    ]


class LoginPage(HTMLPage):
    def login(self, login, password):
        form = self.get_form('//form[@action="/j_security_check"]')
        form['j_username'] = login
        form['j_password'] = password
        form.submit()

    def get_error(self):
        return CleanText('//div[contains(text(), "Erreur")]')(self.doc)


class AccountsPage(LoggedPage, HTMLPage):
    @method
    class iter_accounts(ListElement):
        item_xpath = '//div[@class="bk-contrat theme-epargne"]'

        class item(ItemElement):
            klass = Account

            obj_id = CleanText('.//div[@class="infos-contrat"]//strong')
            obj_label = CleanText('.//div[@class="type-contrat"]//h2')
            obj_type = Account.TYPE_LIFE_INSURANCE
            obj_balance = CleanDecimal(CleanText('.//div[@class="col-right"]', children=False), replace_dots=True, default=NotAvailable)
            obj_currency = Currency(CleanText(u'.//div[@class="col-right"]', children=False, replace=[("Au", "")]))

    def get_detail_page_parameters(self, account):
        """
        Get parameters for the request that leads to the transactions/investments page
        """
        data = []

        # parameter 1
        el = self.doc.xpath('//div[@class="infos-contrat"][descendant::strong[contains(text(), $contract_id)]]/parent::div//div[@class="zone-detail"]//span/a', contract_id=account.id)
        assert len(el) == 1
        parameter = Regexp(Attr('.', 'onclick'), r".*,\{'(.*)':'(.*)'\},.*\);return false", '\\1 \\2')(el[0]).split(' ')
        data.append((parameter[0], parameter[1]))

        form = self.get_form(id='j_idt254')
        # parameter 2
        data.append(('javax.faces.ViewState', form['javax.faces.ViewState']))
        # parameter 3
        data.append(('j_idt254', form['j_idt254']))

        return form.url, data


class InvestmentsParser(TableElement):
        col_label = 'Support'
        col_share = 'Répartition en %'
        col_valuation = 'Montant'
        col_unitvalue = "Valeur de l'unité de compte"

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(TableCell('label'))
            obj_portfolio_share = Eval(lambda x: x/100, CleanDecimal(TableCell('share'), replace_dots=True))
            obj_valuation = CleanDecimal(TableCell('valuation'), replace_dots=True)
            obj_unitvalue = CleanDecimal(TableCell('unitvalue'), replace_dots=True, default=NotAvailable)
            obj_quantity = CleanDecimal(TableCell('quantity'), default=NotAvailable)


class TransactionsParser(object):
    @method
    class iter_history(ListElement):
        item_xpath = '//div[contains(@id, "listeMouvements")]/table//tr[position()>1]'

        class item(ItemElement):
            klass = Transaction

            obj_rdate = obj_date = Date(CleanText('./td[1]'))
            obj_raw = Transaction.Raw('./td[2]')
            obj_amount = CleanDecimal('./td[3]', replace_dots=True)
            obj__detail_id = Regexp(Attr('./td[4]/a', 'href'), r'popin(\d+)')

            def obj_investments(self):
                detail_id = Field('_detail_id')(self)
                investment_details = self.page.doc.xpath('//div[@id="popin{}"]'.format(detail_id))
                assert len(investment_details) == 1
                return list(self.get_investments(self.page, el=investment_details[0]))

            class get_investments(InvestmentsParser):
                item_xpath = './p[strong[contains(text(), "Répartition de votre versement") or contains(text(), "Réinvestissement") or contains(text(), "Désinvestissement")]]/following-sibling::table//tr[position()>1]'
                head_xpath = './p[strong[contains(text(), "Répartition de votre versement") or contains(text(), "Réinvestissement") or contains(text(), "Désinvestissement")]]/following-sibling::table//tr[1]/th'
                col_quantity = re.compile("Nombre")  # use regex because the column name tends to be inconsistent between the tables


class TransactionsInvestmentsPage(LoggedPage, HTMLPage, TransactionsParser):
    def show_all_transactions(self):
        # show all transactions if many of them
        if self.doc.xpath('//span[contains(text(), "Plus de mouvements financiers")]'):
            try:
                form = self.get_form(name="formStep1")

                # have a look to the javascript file called 'jsf.js.faces' and
                # to the js listener "mojarra.ab" to understand
                # All parameters can be hardcoded
                form['javax.faces.source'] = 'formStep1:tabOnglets:plusDeMouvementFinancier'
                form['javax.faces.partial.event'] = 'click'
                form['javax.faces.partial.execute'] = 'formStep1:tabOnglets:plusDeMouvementFinancier'
                form['javax.faces.partial.render'] = 'formStep1:tabOnglets:listeMouvements formStep1:tabOnglets:gPlusDeMouvementFinancier formStep1:tabOnglets:gMoinsDeMouvementFinancier formStep1:tabOnglets:listPopinMouvement'
                form['javax.faces.behavior.event'] = 'click'
                form['javax.faces.partial.ajax'] = "true"

                form.submit()
            except FormNotFound:
                pass

    def has_investments(self):
        if self.doc.xpath('//li/a[text()="Portefeuille"]'):
            return True

    @method
    class iter_investments(InvestmentsParser):
        item_xpath = '//div[h3[text()="Répartition de votre portefeuille"]]/table//tr[position()>1]'
        head_xpath = '//div[h3[text()="Répartition de votre portefeuille"]]/table//tr[1]/th'
        col_quantity = "Nombre d'unités de comptes"


class AllTransactionsPage(LoggedPage, XMLPage, HTMLPage, TransactionsParser):
    def build_doc(self, content):
        # HTML embedded in XML: parse XML first then extract the html
        xml = XMLPage.build_doc(self, content)
        transactions_html = xml.xpath('//partial-response/changes/update[1]')[0].text.encode(encoding=self.encoding)
        investments_html = xml.xpath('//partial-response/changes/update[2]')[0].text.encode(encoding=self.encoding)
        html = transactions_html + investments_html
        return HTMLPage.build_doc(self, html)
