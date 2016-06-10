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
from weboob.browser.elements import ItemElement, TableElement, SkipItem, method
from weboob.browser.filters.standard import CleanText, Date, Regexp, CleanDecimal, Env, TableCell, Field, Async, AsyncLoad
from weboob.browser.filters.html import Attr, Link
from weboob.capabilities.bank import Account, Investment, Transaction
from weboob.capabilities.base import NotAvailable


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)


class LoginPage(HTMLPage):
    def login(self, login, password):
        form = self.get_form('//form[@id="loginForm"]')
        form['loginForm:name'] = login
        form['loginForm:password'] = password
        form['loginForm:login'] = "loginForm:login"
        form.submit()


class AccountsPage(LoggedPage, HTMLPage):
    TYPES = {'Assurance Vie': Account.TYPE_LIFE_INSURANCE, 'Unknown': Account.TYPE_UNKNOWN}

    @method
    class iter_accounts(TableElement):
        item_xpath = '//table[@role]/tbody/tr'
        head_xpath = '//table[@role]/thead/tr/th'

        col_label = u'Produit'
        col_id = u'Numéro de contrat'
        col_balance = u'Montant (€)'

        class item(ItemElement):
            klass = Account

            load_details = Field('_link') & AsyncLoad

            obj_id = CleanText(TableCell('id'), replace=[(' ', '')])
            obj_label = CleanText(TableCell('label'))
            obj_balance = MyDecimal(TableCell('balance'))
            obj_valuation_diff = Async('details') & MyDecimal('//tr[1]/td[contains(text(), \
                                    "value du contrat")]/following-sibling::td')
            obj__link = Link('.//a')

            def obj_type(self):
                return self.page.TYPES[Async('details', CleanText('//td[contains(text(), \
                    "Option fiscale")]/following-sibling::td', default="Unknown"))(self)]


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
    class iter_investment(TableElement):
        item_xpath = '//div[contains(@id, "INVESTISSEMENT")]//table/tbody/tr[@data-ri]'
        head_xpath = '//div[contains(@id, "INVESTISSEMENT")]//table/thead/tr/th'

        col_label = u'Support'
        col_vdate = u'Date de valeur'
        col_unitvalue = u'Valeur de part'
        col_quantity = u'Nombre de parts'
        col_valuation = re.compile('Contre')
        col_portfolio_share = u'%'

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(TableCell('label'))
            obj_code = Regexp(CleanText('.//td[contains(text(), "Isin")]'), ':[\s]+([\w]+)', default=NotAvailable)
            obj_quantity = MyDecimal(TableCell('quantity'))
            obj_unitvalue = MyDecimal(TableCell('unitvalue'))
            obj_valuation = MyDecimal(TableCell('valuation'))
            obj_vdate = Date(CleanText(TableCell('vdate')), dayfirst=True, default=NotAvailable)
            obj_portfolio_share = MyDecimal(TableCell('portfolio_share'))

            def obj_unitprice(self):
                return MyDecimal('//div[contains(@id, "PRIX_REVIENT")]//a[contains(text(), \
                            "%s")]/ancestor::tr/td[5]' % Field('label')(self))(self)

            def obj_diff(self):
                return MyDecimal('//div[contains(@id, "PRIX_REVIENT")]//a[contains(text(), \
                            "%s")]/ancestor::tr/td[6]' % Field('label')(self))(self)

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

    def get_investments(self, el, xpath='.'):
        # Get all positions of th
        positions = {}
        keys = {'isin': 'code', 'support': 'label', 'supports': 'label', 'nombre de parts': 'quantity', 'valeur de part': \
                'unitvalue', 'montant brut': 'valuation', 'date de valeur': 'vdate', '%': 'portfolio_share'}
        for position, th in enumerate(el.xpath("%s//thead//th" % xpath)):
            key = CleanText().filter(th.xpath('.')).lower()
            if key in keys:
                positions[keys[key]] = position + 1

        investments = []
        for tr in el.xpath("%s//tbody/tr[@data-ri]" % xpath):
            i = Investment()
            i.label = CleanText().filter(tr.xpath('./td[%s]' % positions['label'])) \
                if "label"  in positions else NotAvailable
            i.code = Regexp(CleanText('./td[%s]' % positions['code']), pattern='([A-Z]{2}\d{10})', default=NotAvailable)(tr)
            i.quantity = MyDecimal().filter(tr.xpath('./td[%s]' % positions['quantity'])) \
                if "quantity"  in positions else NotAvailable
            i.unitvalue = MyDecimal().filter(tr.xpath('./td[%s]' % positions['unitvalue'])) \
                if "unitvalue"  in positions else NotAvailable
            i.valuation = MyDecimal().filter(tr.xpath('./td[%s]' % positions['valuation'])) \
                if "valuation"  in positions else NotAvailable
            i.vdate = Date(CleanText('./td[%s]' % positions['vdate']), dayfirst=True, default=NotAvailable)(tr) \
                if "vdate"  in positions else NotAvailable
            i.portfolio_share = MyDecimal().filter(tr.xpath('./td[%s]' % positions['portfolio_share'])) \
                if "portfolio_share"  in positions else NotAvailable
            investments.append(i)

        return investments

    @method
    class iter_history(TableElement):
        item_xpath = '//table/tbody[@id and not(contains(@id, "j_idt"))]/tr[@data-ri]'
        head_xpath = '//table/thead[@id and not(contains(@id, "j_idt"))]/tr/th'

        col_label = u'Type'
        col_status = u'Etat'
        col_brut = u'Montant brut'
        col_net = u'Montant net'
        col_date = u'Date de réception'
        col_vdate = u'Date de valeur'

        class item(ItemElement):
            klass = Transaction

            obj_label = CleanText(TableCell('label'))
            obj_vdate = Date(CleanText(TableCell('vdate')), dayfirst=True)
            obj_type = Transaction.TYPE_BANK
            obj_investments = Env('investments')

            def obj_amount(self):
                amount = MyDecimal(TableCell('net') if not CleanText(TableCell('brut'))(self) else TableCell('brut'))(self)
                return -amount if amount and any(word in Field('label')(self).lower() for word in self.page.DEBIT_WORDS) else amount

            def obj_date(self):
                return Date(CleanText(TableCell('date')), dayfirst=True, default=Field('vdate')(self))(self)

            def condition(self):
                return u"Validé" in CleanText(TableCell('status'))(self)

            def parse(self, el):
                if u"Désinvestir" in CleanText('./following-sibling::tr[1]')(self):
                    self.page.browser.skipped.append([el, el.xpath('./following-sibling::tr[1]')[0]])
                    raise SkipItem()

                self.env['investments'] = self.page.get_investments(el, \
                    './following-sibling::tr[1]//span[contains(text(), "ISIN")]/ancestor::table[1]')

    def iter_history_skipped(self):
        for tr1, tr2 in self.browser.skipped:
            for table, h2 in zip(tr2.xpath('.//table[@role]'), tr2.xpath(u'.//h2')):
                t = Transaction()

                t.vdate = Date(CleanText('./td[8]'), dayfirst=True)(tr1)
                t.date = Date(CleanText('./td[6]'), dayfirst=True, default=t.vdate)(tr1)
                t.type = Transaction.TYPE_BANK
                t.label = u"%s - %s" % (CleanText().filter(tr1.xpath('./td[2]')), \
                                        CleanText().filter(h2.xpath('.')))
                t.amount = CleanDecimal(replace_dots=True, default=MyDecimal().filter( \
                                        tr1.xpath('./td[5]'))).filter(tr1.xpath('./td[4]'))

                if t.amount and any(word in t.label.lower() for word in self.DEBIT_WORDS):
                    t.amount = -t.amount

                t.investments = self.get_investments(table)

                yield t
