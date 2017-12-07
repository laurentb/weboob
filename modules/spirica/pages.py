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

from __future__ import unicode_literals

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
    obj_code = Regexp(CleanText('.//td[contains(text(), "Isin")]'), ':[\s]+([\w]+)', default=NotAvailable)

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

    def goto_unitprice(self):
        form = self.get_form(id='ongletSituation:syntheseContrat')
        form['javax.faces.source'] = 'ongletSituation:ongletContratTab'
        form['javax.faces.partial.execute'] = 'ongletSituation:ongletContratTab'
        form['javax.faces.partial.render'] = 'ongletSituation:ongletContratTab'
        form['javax.faces.behavior.event'] = 'tabChange'
        form['javax.faces.partial.event'] = 'tabChange'
        form['ongletSituation:ongletContratTab_newTab'] = 'ongletSituation:ongletContratTab:PRIX_REVIENT_MOYEN'
        form['ongletSituation:ongletContratTab_tabindex'] = '1'
        form.submit()

    @method
    class iter_investment(TableInvestment):
        item_xpath = '//div[contains(@id,"INVESTISSEMENT")]//div[ends-with(@id, ":tableDetailSituationCompte")]//table/tbody/tr[@data-ri]'
        head_xpath = '//div[contains(@id,"INVESTISSEMENT")]//div[ends-with(@id, ":tableDetailSituationCompte")]//table/thead/tr/th'

        col_valuation = re.compile('Contre')

        class item(ItemInvestment):
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

    @method
    class iter_pm_investment(TableInvestment):
        item_xpath = '//div[contains(@id,"PRIX_REVIENT_MOYEN")]//div[ends-with(@id, ":tableDetailSituationCompte")]//table/tbody/tr[@data-ri]'
        head_xpath = '//div[contains(@id,"PRIX_REVIENT_MOYEN")]//div[ends-with(@id, ":tableDetailSituationCompte")]//table/thead/tr/th'

        col_diff = re.compile(u'.*PRM en €')
        col_diff_percent = re.compile('.*PRM en %')
        col_unitprice = re.compile('.*Prix de Revient Moyen')

        class item(ItemInvestment):
            obj_diff = MyDecimal(TableCell('diff'), default=NotAvailable)
            obj_diff_percent = Eval(lambda x: x/100, MyDecimal(TableCell('diff_percent')))
            obj_unitprice = MyDecimal(TableCell('unitprice'))

            def obj_diff_percent(self):
                diff_percent = MyDecimal(TableCell('diff_percent'))(self)
                if diff_percent:
                    return diff_percent / 100
                else:
                    return NotAvailable

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

    def go_historytab(self):
        form = self.get_form(id='ongletSituation:syntheseContrat')
        form['javax.faces.source'] = 'tabsPrincipauxConsultationContrat'
        form['javax.faces.partial.execute'] = 'tabsPrincipauxConsultationContrat'
        form['javax.faces.partial.render'] = 'tabsPrincipauxConsultationContrat'
        form['javax.faces.behavior.event'] = 'tabChange'
        form['javax.faces.partial.event'] = 'tabChange'
        form['tabsPrincipauxConsultationContrat_contentLoad'] = 'true'
        form['tabsPrincipauxConsultationContrat_newTab'] = 'HISTORIQUE_OPERATIONS'
        form['ongletSituation:ongletContratTab_tabindex'] = '1'
        form.submit()

    def go_historyall(self):
        id_ = Attr('//a[contains(text(), "Tout afficher")]', 'id', default=None)(self.doc)
        if id_:
            form = self.get_form(xpath='//form[contains(@id, "ongletHistoOperations:ongletHistoriqueOperations")]')
            form['javax.faces.partial.execute'] = '@all'
            form['javax.faces.partial.render'] = 'ongletHistoOperations:ongletHistoriqueOperations:newoperations'
            form[id_] = id_
            form['javax.faces.source'] = id_
            form.submit()

    def get_historyexpandall_form(self, data):
        form = self.get_form(xpath='//form[contains(@id, "ongletHistoOperations:ongletHistoriqueOperations")]')
        form['javax.faces.behavior.event'] = 'rowToggle'
        form['javax.faces.partial.event'] = 'rowToggle'
        id_ = Attr('//div[contains(@id, "ongletHistoOperations:ongletHistoriqueOperations")][has-class("listeAvecDetail")]', 'id')(self.doc)
        form['javax.faces.source'] = id_
        form['javax.faces.partial.execute'] = id_
        form['javax.faces.partial.render'] = id_ + ':detail ' + id_
        form[id_ + '_rowExpansion'] = 'true'
        form[id_ + '_encodeFeature'] = 'true'
        form[id_ + '_expandedRowIndex'] = data
        return form

    @method
    class iter_history(TableElement):
        item_xpath = '//table[@role]/tbody[@id]/tr[@data-ri]'
        head_xpath = '//table[@role]/thead[@id]/tr/th'

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
                data = Attr('.', 'data-ri')(self)
                form = self.page.get_historyexpandall_form(data)
                page = self.page.browser.open(form.url, data=dict(form)).page
                investments = []
                for table in page.doc.xpath('//following-sibling::tr[1]//span[contains(text(), "ISIN")]/ancestor::table[1]'):
                    investments.extend(TableTransactionsInvestment(self.page, el=table)())
                return investments
