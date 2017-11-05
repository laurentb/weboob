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

import re

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.elements import ItemElement, TableElement, method
from weboob.browser.filters.standard import CleanText, Date, Regexp, CleanDecimal, \
                                            Field, Async, AsyncLoad, Eval
from weboob.browser.filters.html import Attr, Link, TableCell
from weboob.capabilities.bank import Account, Investment, Transaction
from weboob.capabilities.base import NotAvailable, empty
from weboob.exceptions import BrowserUnavailable
from weboob.tools.compat import urljoin


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)


class MaintenancePage(HTMLPage):
   def on_load(self):
        raise BrowserUnavailable(CleanText().filter(self.doc.xpath('//p')))


class LoginPage(HTMLPage):
    def login(self, login, password):
        form = self.get_form('//form[@id="loginForm"]')
        form['loginForm:name'] = login
        form['loginForm:password'] = password
        form['loginForm:login'] = "loginForm:login"
        form.submit()

    def get_error(self):
        return CleanText('//li[@class="erreurBox"]')(self.doc)


class AccountsPage(LoggedPage, HTMLPage):
    TYPES = {
        'Assurance Vie': Account.TYPE_LIFE_INSURANCE,
        'Capitalisation': Account.TYPE_MARKET,
        'Unknown': Account.TYPE_UNKNOWN,
    }

    @method
    class iter_accounts(TableElement):
        item_xpath = '//table[@role]/tbody/tr'
        head_xpath = '//table[@role]/thead/tr/th'

        col_label = u'Produit'
        col_id = u'Numéro de contrat'
        col_balance = u'Montant (€)'

        class item(ItemElement):
            klass = Account

            load_details = Field('url') & AsyncLoad

            obj_id = CleanText(TableCell('id'), replace=[(' ', '')])
            obj_label = CleanText(TableCell('label'))
            obj_balance = MyDecimal(TableCell('balance'))
            obj_valuation_diff = Async('details') & MyDecimal('//tr[1]/td[contains(text(), \
                                    "value du contrat")]/following-sibling::td')

            def obj_url(self):
                return urljoin(self.page.url, Link('.//a')(self))

            def obj_type(self):
                return self.page.TYPES[Async('details', CleanText('//td[contains(text(), \
                    "Option fiscale")]/following-sibling::td', default="Unknown"))(self)]


class TableInvestment(TableElement):
    col_label = u'Support'
    col_vdate = u'Date de valeur'
    col_unitvalue = u'Valeur de part'
    col_quantity = u'Nombre de parts'
    col_portfolio_share = u'%'


class ItemInvestment(ItemElement):
    klass = Investment

    obj_label = CleanText(TableCell('label'))
    obj_quantity = MyDecimal(TableCell('quantity', default=None))
    obj_unitvalue = MyDecimal(TableCell('unitvalue', default=None))
    obj_vdate = Date(CleanText(TableCell('vdate', default="")), dayfirst=True, default=NotAvailable)

    def obj_valuation(self):
        valuation = MyDecimal(TableCell('valuation', default=None))(self)
        h2 = CleanText('./ancestor::div[contains(@id, "Histo")][1]/preceding-sibling::h2[1]')(self)
        return -valuation if valuation and any(word in h2.lower() for word in self.page.DEBIT_WORDS) else valuation

    def obj_portfolio_share(self):
        ps = MyDecimal(TableCell('portfolio_share', default=None))(self)
        return Eval(lambda x: x / 100, ps)(self) if not empty(ps) else NotAvailable


class TableTransactionsInvestment(TableInvestment):
    item_xpath = './tbody/tr'
    head_xpath = './thead/tr/th'

    col_code = u'ISIN'
    col_valuation = [u'Montant brut', u'Montant net']

    class item(ItemInvestment):
        obj_code = Regexp(CleanText(TableCell('code')), pattern='([A-Z]{2}\d{10})', default=NotAvailable)


class ProfileTableInvestment(TableInvestment):
    # used only when portfolio is divided in multiple "profiles"
    head_xpath = '//thead[ends-with(@id, ":contratProfilTable_head")]/tr/th'


class DetailsPage(LoggedPage, HTMLPage):
    DEBIT_WORDS = [u'arrêté', 'rachat', 'frais', u'désinvestir']

    def get_investment_form(self):
        form = self.get_form('//form[contains(@id, "j_idt")]')
        form['ongletSituation:ongletContratTab_newTab'] = \
                Link().filter(self.doc.xpath('//a[contains(text(), "Prix de revient moyen")]'))[1:]
        form['javax.faces.source'] = "ongletSituation:ongletContratTab"
        form['javax.faces.behavior.event'] = "tabChange"
        return form

    @method
    class iter_investment(TableInvestment):
        item_xpath = '//div[contains(@id,"INVESTISSEMENT")]//div[ends-with(@id, ":tableDetailSituationCompte")]//table/tbody/tr[@data-ri]'
        head_xpath = '//div[contains(@id,"INVESTISSEMENT")]//div[ends-with(@id, ":tableDetailSituationCompte")]//table/thead/tr/th'

        col_valuation = re.compile('Contre')

        class item(ItemInvestment):
            obj_code = Regexp(CleanText('.//td[contains(text(), "Isin")]'), ':[\s]+([\w]+)', default=NotAvailable)

            def invest_link(self):
                label = Field('label')(self)
                for a in self.el.xpath('//div[contains(@id, "PRIX_REVIENT")]//a'):
                    if label in CleanText('.')(a):
                        return a
                assert 'fonds euro' in label.lower()

            def obj_unitprice(self):
                link = self.invest_link()
                if link:
                    return MyDecimal('./ancestor::tr/td[5]')(link)

            def obj_diff(self):
                link = self.invest_link()
                if link:
                    return MyDecimal('./ancestor::tr/td[6]')(link)

            def obj_portfolio_share(self):
                inv_share = ItemInvestment.obj_portfolio_share(self)
                if self.xpath('ancestor::tbody[ends-with(@id, "contratProfilTable_data")]'):
                    # investments are nested in profiles, row share is relative to profile share
                    profile_table_el = self.xpath('ancestor::tr/ancestor::table[position() = 1]')[0]
                    profile_table = ProfileTableInvestment(self.page, self, profile_table_el)
                    share_idx = profile_table.get_colnum('portfolio_share')
                    assert share_idx

                    path = 'ancestor::tr/preceding-sibling::tr[@data-ri][position() = 1][1]/td[%d]' % (share_idx + 1)

                    profile_share = MyDecimal(path)(self)
                    assert profile_share
                    #raise Exception('dtc')
                    profile_share = Eval(lambda x: x / 100, profile_share)(self)
                    return inv_share * profile_share
                else:
                    return inv_share

    def get_historytab_form(self):
        form = self.get_form('//form[contains(@id, "j_idt")]')
        idt = Attr(None, 'name').filter(self.doc.xpath('//input[contains(@name, "j_idt") \
                        and contains(@name, "activeIndex")]')).rsplit('_', 1)[0]
        form['%s_contentLoad' % idt] = "true"
        form['%s_newTab' % idt] = Link().filter(self.doc.xpath('//a[contains(@href, "HISTORIQUE")]'))[1:]
        form['%s_activeIndex' % idt] = "1"
        form['javax.faces.source'] = idt
        form['javax.faces.behavior.event'] = "tabChange"
        return form

    def get_historyallpages_form(self):
        onclick = self.doc.xpath('//a[contains(text(), "Tout")]/@onclick')
        if onclick:
            idt = re.search('{[^\w]+([\w\d:]+)', onclick[0]).group(1)
            form = self.get_form('//form[contains(@id, "j_idt")]')
            form[idt] = idt
            return form
        return False

    def get_historyexpandall_form(self):
        form = self.get_form('//form[contains(@id, "j_idt")]')
        form['javax.faces.source'] = "ongletHistoOperations:newoperations"
        form['javax.faces.behavior.event'] = "rowToggle"
        form['ongletHistoOperations:newoperations_rowExpansion'] = "true"
        for data in self.doc.xpath('//tr[@data-ri]/@data-ri'):
            form['ongletHistoOperations:newoperations_expandedRowIndex'] = data
            yield form

    @method
    class iter_history(TableElement):
        item_xpath = '//table/tbody[@id and not(contains(@id, "j_idt"))]/tr[@data-ri]'
        head_xpath = '//table/thead[@id and not(contains(@id, "j_idt"))]/tr/th'

        col_label = u'Type'
        col_status = u'Etat'
        col_brut = [u'Montant brut', u'Brut']
        col_net = [u'Montant net', u'Net']
        col_date = u'Date de réception'
        col_vdate = u'Date de valeur'

        class item(ItemElement):
            klass = Transaction

            obj_label = CleanText(TableCell('label'))
            obj_vdate = Date(CleanText(TableCell('vdate')), dayfirst=True)
            obj_type = Transaction.TYPE_BANK

            def obj_amount(self):
                amount = MyDecimal(TableCell('net') if not CleanText(TableCell('brut'))(self) else TableCell('brut'))(self)
                return -amount if amount and any(word in Field('label')(self).lower() for word in self.page.DEBIT_WORDS) else amount

            def obj_date(self):
                return Date(CleanText(TableCell('date')), dayfirst=True, default=Field('vdate')(self))(self)

            def condition(self):
                return u"Validé" in CleanText(TableCell('status'))(self) and u"Arrêté annuel" not in Field('label')(self)

            def obj_investments(self):
                investments = []
                for table in self.el.xpath('./following-sibling::tr[1]//span[contains(text(), "ISIN")]/ancestor::table[1]'):
                    investments.extend(TableTransactionsInvestment(self.page, el=table)())
                return investments
