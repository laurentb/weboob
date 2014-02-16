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

from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.browser import BasePage


__all__ = ['AccountHistory', 'CardsList']


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(u'^(?P<category>CHEQUE)( N)? (?P<text>.*)'),        FrenchTransaction.TYPE_CHECK),
                (re.compile(r'^(?P<category>ACHAT CB) (?P<text>.*) (?P<dd>\d{2})\.(?P<mm>\d{2}).(?P<yy>\d{2}).*'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile('^(?P<category>(PRELEVEMENT DE|TELEREGLEMENT|TIP)) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^(?P<category>ECHEANCEPRET)(?P<text>.*)'),   FrenchTransaction.TYPE_LOAN_PAYMENT),
   (re.compile('^CARTE \w+ (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2}) A (?P<HH>\d+)H(?P<MM>\d+) (?P<category>RETRAIT DAB) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^(?P<category>RETRAIT DAB) (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2}) (?P<HH>\d+)H(?P<MM>\d+) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^(?P<category>VIR(EMEN)?T?) (DE |POUR )?(?P<text>.*)'),
                                                            FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^(?P<category>REMBOURST)(?P<text>.*)'),     FrenchTransaction.TYPE_PAYBACK),
                (re.compile('^(?P<category>COMMISSIONS)(?P<text>.*)'),   FrenchTransaction.TYPE_BANK),
                (re.compile('^(?P<category>FRAIS POUR)(?P<text>.*)'),    FrenchTransaction.TYPE_BANK),
                (re.compile('^(?P<text>(?P<category>REMUNERATION).*)'),   FrenchTransaction.TYPE_BANK),
                (re.compile('^(?P<category>REMISE DE CHEQUES?) (?P<text>.*)'), FrenchTransaction.TYPE_DEPOSIT),
               ]


class AccountHistory(BasePage):
    def get_next_link(self):
        for a in self.document.xpath('//a[@class="btn_crt"]'):
            txt = u''.join([txt.strip() for txt in a.itertext()])
            if u'mois précédent' in txt:
                return a.attrib['href']

    def get_history(self, deferred=False):
        """
        deffered is True when we are on a card page.
        """
        mvt_table = self.document.xpath("//table[@id='mouvements']", smart_strings=False)[0]
        mvt_ligne = mvt_table.xpath("./tbody/tr")

        operations = []

        if deferred:
            # look for the debit date, and if it is already debited
            txt = u''.join([txt.strip() for txt in self.document.xpath('//div[@class="infosynthese"]')[0].itertext()])
            m = re.search('(\d+)/(\d+)/(\d+)', txt)
            if m:
                debit_date = datetime.date(*map(int, reversed(m.groups())))
            coming = 'En cours' in txt
        else:
            coming = False

        for mvt in mvt_ligne:
            op = Transaction(len(operations))
            op.parse(date=mvt.xpath("./td/span")[0].text.strip(),
                     raw=unicode(self.parser.tocleanstring(mvt.xpath('./td/span')[1]).strip()))

            if op.label.startswith('DEBIT CARTE BANCAIRE DIFFERE'):
                continue

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
                op.rdate = op.date
                op.date = debit_date
                # on card page, amounts are without sign
                if op.amount > 0:
                    op.amount = - op.amount

            op._coming = coming

            operations.append(op)
        return operations


class CardsList(BasePage):
    def get_cards(self):
        cards = []
        for tr in self.document.xpath('//table[@class="dataNum"]/tbody/tr'):
            cards.append(tr.xpath('.//a')[0].attrib['href'])

        return cards
