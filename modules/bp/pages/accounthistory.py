# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Nicolas Duhamel
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
import re

from weboob.capabilities.base import NotAvailable
from weboob.capabilities.bank import Investment, Transaction as BaseTransaction
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.browser.pages import LoggedPage
from weboob.browser.elements import TableElement, ItemElement, method
from weboob.browser.filters.html import Link
from weboob.browser.filters.standard import CleanDecimal, CleanText, Eval, TableCell, Async, AsyncLoad, Date

from .base import MyHTMLPage


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(u'^(?P<category>CHEQUE)( N)? (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_CHECK),
                (re.compile(r'^(?P<category>ACHAT CB) (?P<text>.*) (?P<dd>\d{2})\.(?P<mm>\d{2}).(?P<yy>\d{2}).*'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile('^(?P<category>(PRELEVEMENT DE|TELEREGLEMENT|TIP)) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^(?P<category>ECHEANCEPRET)(?P<text>.*)'),
                                                            FrenchTransaction.TYPE_LOAN_PAYMENT),
                (re.compile(r'^CARTE \w+ (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2}) A (?P<HH>\d+)H(?P<MM>\d+) (?P<category>RETRAIT DAB) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(r'^(?P<category>RETRAIT DAB) (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2}) (?P<HH>\d+)H(?P<MM>\d+) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(r'^(?P<category>RETRAIT) (?P<text>.*) (?P<dd>\d{2})\.(?P<mm>\d{2})\.(?P<yy>\d{2})'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^(?P<category>VIR(EMEN)?T?) (DE |POUR )?(?P<text>.*)'),
                                                            FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^(?P<category>REMBOURST)(?P<text>.*)'),     FrenchTransaction.TYPE_PAYBACK),
                (re.compile('^(?P<category>COMMISSIONS)(?P<text>.*)'),   FrenchTransaction.TYPE_BANK),
                (re.compile('^(?P<category>FRAIS POUR)(?P<text>.*)'),    FrenchTransaction.TYPE_BANK),
                (re.compile('^(?P<text>(?P<category>REMUNERATION).*)'),   FrenchTransaction.TYPE_BANK),
                (re.compile('^(?P<category>REMISE DE CHEQUES?) (?P<text>.*)'), FrenchTransaction.TYPE_DEPOSIT),
                (re.compile(u'^(?P<text>DEBIT CARTE BANCAIRE DIFFERE.*)'), FrenchTransaction.TYPE_CARD_SUMMARY),
               ]


class AccountHistory(LoggedPage, MyHTMLPage):
    def get_next_link(self):
        for a in self.doc.xpath('//a[@class="btn_crt"]'):
            txt = u''.join([txt.strip() for txt in a.itertext()])
            if u'mois précédent' in txt:
                return a.attrib['href']

    def get_history(self, deferred=False):
        """
        deffered is True when we are on a card page.
        """
        mvt_table = self.doc.xpath("//table[@id='mouvements']", smart_strings=False)[0]
        mvt_ligne = mvt_table.xpath("./tbody/tr")

        operations = []

        if deferred:
            # look for the card number, debit date, and if it is already debited
            txt = u''.join([txt.strip() for txt in self.doc.xpath('//div[@class="infosynthese"]')[0].itertext()])
            m = re.search(u'sur votre carte n°\*\*\*\*\*\*(\d+)\*', txt)
            card_no = u'inconnu'
            if m:
                card_no = m.group(1)

            m = re.search('(\d+)/(\d+)/(\d+)', txt)
            if m:
                debit_date = datetime.date(*map(int, reversed(m.groups())))
            coming = 'En cours' in txt
        else:
            coming = False

        for mvt in mvt_ligne:
            op = Transaction()
            op.parse(date=CleanText('./td[1]/span')(mvt),
                     raw=CleanText('./td[2]/span')(mvt))

            if op.label.startswith('DEBIT CARTE BANCAIRE DIFFERE'):
                op.deleted = True

            r = re.compile(r'\d+')

            tmp = mvt.xpath("./td/span/strong")
            if not tmp:
                tmp = mvt.xpath("./td/span")
            amount = None
            for t in tmp:
                if r.search(t.text):
                    amount = t.text

            op.set_amount(amount)

            if deferred:
                op._cardid = 'CARTE %s' % card_no
                op.type = Transaction.TYPE_DEFERRED_CARD
                op.rdate = op.date
                op.date = debit_date
                # on card page, amounts are without sign
                if op.amount > 0:
                    op.amount = - op.amount

            op.rdate = datetime.datetime.combine(op.rdate, datetime.time())

            op._coming = coming

            operations.append(op)
        return operations


class CardsList(LoggedPage, MyHTMLPage):
    def get_cards(self):
        cards = []
        for tr in self.doc.xpath('//table[@class="dataNum"]/tbody/tr'):
            cards.append(tr.xpath('.//a')[0].attrib['href'])

        return cards


class SavingAccountSummary(LoggedPage, MyHTMLPage):
    def on_load(self):
        self.browser.location(Link('//ul[has-class("tabs")]//a[@title="Historique des mouvements"]')(self.doc))


class InvestTable(TableElement):
    col_label = 'Support'
    col_share = 'Poids en %'
    col_quantity = 'Nb U.C'
    col_valuation = re.compile('Montant')


class InvestItem(ItemElement):
    klass = Investment

    obj_label = CleanText(TableCell('label', support_th=True))
    obj_portfolio_share = Eval(lambda x: x / 100 if x else NotAvailable, CleanDecimal(TableCell('share', support_th=True), replace_dots=True, default=NotAvailable))
    obj_quantity = CleanDecimal(TableCell('quantity', support_th=True), replace_dots=True, default=NotAvailable)
    obj_valuation = CleanDecimal(TableCell('valuation', support_th=True), replace_dots=True, default=NotAvailable)


class LifeInsuranceInvest(LoggedPage, MyHTMLPage):
    def has_error(self):
        return 'erreur' in CleanText('//p[has-class("titlePage")]')(self.doc)

    @method
    class iter_investments(InvestTable):
        head_xpath = '//table[starts-with(@id, "mouvements")]/thead//th'
        item_xpath = '//table[starts-with(@id, "mouvements")]/tbody//tr'

        col_unitvalue = 'Valeur Liquidative'

        class item(InvestItem):
            obj_unitvalue = CleanDecimal(TableCell('unitvalue'), replace_dots=True, default=NotAvailable)


class LifeInsuranceHistory(LoggedPage, MyHTMLPage):
    @method
    class iter_transactions(TableElement):
        head_xpath = '//table[@id="options"]/thead//th'
        item_xpath = '//table[@id="options"]/tbody//tr'

        col_date = 'Date de valeur'
        col_amount = 'Montant'
        col_label = u"Type d'opération"

        class item(ItemElement):
            klass = BaseTransaction

            obj_label = CleanText(TableCell('label'))
            obj_amount = CleanDecimal(TableCell('amount'), replace_dots=True)
            obj_date = Date(CleanText(TableCell('date')))
            obj__coming = False

            load_invs = Link('.//a') & AsyncLoad

            def obj_investments(self):
                page = Async('invs').loaded_page(self)
                return list(page.iter_investments())


class LifeInsuranceHistoryInv(LoggedPage, MyHTMLPage):
    @method
    class iter_investments(InvestTable):
        head_xpath = '//table/thead//th'
        item_xpath = '//table/tbody//tr[position() > 1 and position() < last()]'

        class item(InvestItem):
            pass


class RetirementHistory(LoggedPage, MyHTMLPage):
    @method
    class get_history(TableElement):
        head_xpath = '//table[@id="mvt" or @id="options" or @id="mouvements"]/thead//th'
        item_xpath = '//table[@id="mvt" or @id="options" or @id="mouvements"]/tbody//tr'

        col_date = re.compile('Date')
        col_label = u"Type d'opération"
        col_amount = 'Montant'

        class item(ItemElement):
            klass = BaseTransaction

            obj_label = CleanText(TableCell('label'))
            obj_date = Date(CleanText(TableCell('date')))
            obj_amount = CleanDecimal(TableCell('amount'), replace_dots=True)
            obj__coming = False
