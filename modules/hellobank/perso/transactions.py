# -*- coding: utf-8 -*-

# Copyright(C) 2013 Christophe Lampin
# Copyright(C) 2009-2012  Romain Bignon
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

from weboob.deprecated.browser import Page
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(u'^(?P<category>CHEQUE)(?P<text>.*)'),        FrenchTransaction.TYPE_CHECK),
                (re.compile('^(?P<category>FACTURE CARTE) DU (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) (?P<text>.*?)( CA?R?T?E? ?\d*X*\d*)?$'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile('^(?P<category>(PRELEVEMENT|TELEREGLEMENT|TIP)) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^(?P<category>ECHEANCEPRET)(?P<text>.*)'),   FrenchTransaction.TYPE_LOAN_PAYMENT),
                (re.compile('^(?P<category>RETRAIT DAB) (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2})( (?P<HH>\d+)H(?P<MM>\d+))? (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^(?P<category>VIR(EMEN)?T? ((RECU|FAVEUR) TIERS|SEPA RECU)?)( /FRM)?(?P<text>.*)'),
                                                            FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^(?P<category>REMBOURST) CB DU (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_PAYBACK),
                (re.compile('^(?P<category>REMBOURST)(?P<text>.*)'),     FrenchTransaction.TYPE_PAYBACK),
                (re.compile('^(?P<category>COMMISSIONS)(?P<text>.*)'),   FrenchTransaction.TYPE_BANK),
                (re.compile('^(?P<text>(?P<category>REMUNERATION).*)'),   FrenchTransaction.TYPE_BANK),
                (re.compile('^(?P<category>REMISE CHEQUES)(?P<text>.*)'), FrenchTransaction.TYPE_DEPOSIT),
               ]


class AccountHistory(Page):
    def iter_operations(self):
        for tr in self.document.xpath('//table[@id="tableCompte"]//tr'):
            if len(tr.xpath('td[@class="debit"]')) == 0:
                continue

            id = tr.find('td').find('input').attrib['id'].lstrip('_')
            op = Transaction(id)
            op.parse(date=tr.findall('td')[1].text,
                     raw=tr.findall('td')[2].text.replace(u'\xa0', u''))

            debit = tr.xpath('.//td[@class="debit"]')[0].text
            credit = tr.xpath('.//td[@class="credit"]')[0].text

            op.set_amount(credit, debit)

            yield op

    def iter_coming_operations(self):
        i = 0
        for tr in self.document.xpath('//table[@id="tableauOperations"]//tr'):
            if 'typeop' in tr.attrib:
                tds = tr.findall('td')
                if len(tds) != 3:
                    continue

                text = tds[1].text or u''
                text = text.replace(u'\xa0', u'')
                for child in tds[1].getchildren():
                    if child.text:
                        text += child.text
                    if child.tail:
                        text += child.tail

                i += 1
                operation = Transaction(i)
                operation.parse(date=tr.attrib['dateop'],
                                raw=text)
                operation.set_amount(tds[2].text)
                yield operation

    def get_IBAN(self):
        return self.document.xpath('//a[@class="lien_perso_libelle"]')[0].attrib['id'][10:26]


class AccountComing(AccountHistory):
    pass
