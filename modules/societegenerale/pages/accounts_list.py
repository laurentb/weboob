# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Jocelyn Jaubert
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
from urlparse import parse_qs, urlparse
from lxml.etree import XML
from cStringIO import StringIO
from decimal import Decimal, InvalidOperation
import re

from weboob.capabilities.base import empty, NotAvailable
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.browser import BrokenPageError

from .base import BasePage


__all__ = ['AccountsList', 'CardsList', 'AccountHistory']


class AccountsList(BasePage):
    LINKID_REGEXP = re.compile(".*ch4=(\w+).*")

    def on_loaded(self):
        pass

    TYPES = {u'Compte Bancaire':     Account.TYPE_CHECKING,
             u'Compte Epargne':      Account.TYPE_SAVINGS,
             u'Compte Sur Livret':   Account.TYPE_SAVINGS,
             u'Compte Titres':       Account.TYPE_MARKET,
             u'Crédit':              Account.TYPE_LOAN,
             u'Livret':              Account.TYPE_SAVINGS,
             u'PEA':                 Account.TYPE_MARKET,
             u'Plan Epargne':        Account.TYPE_SAVINGS,
             u'Prêt':                Account.TYPE_LOAN,
            }


    def get_list(self):
        for tr in self.document.getiterator('tr'):
            if not 'LGNTableRow' in tr.attrib.get('class', '').split():
                continue

            account = Account()
            for td in tr.getiterator('td'):
                if td.attrib.get('headers', '') == 'TypeCompte':
                    a = td.find('a')
                    if a is None:
                        break
                    account.label = self.parser.tocleanstring(a)
                    for pattern, actype in self.TYPES.iteritems():
                        if account.label.startswith(pattern):
                            account.type = actype
                    account._link_id = a.get('href', '')

                elif td.attrib.get('headers', '') == 'NumeroCompte':
                    account.id = self.parser.tocleanstring(td).replace(u'\xa0', '')

                elif td.attrib.get('headers', '') == 'Libelle':
                    text = self.parser.tocleanstring(td)
                    if text != '':
                        account.label = text

                elif td.attrib.get('headers', '') == 'Solde':
                    div = td.xpath('./div[@class="Solde"]')
                    if len(div) > 0:
                        balance = self.parser.tocleanstring(div[0])
                        if len(balance) > 0 and balance not in ('ANNULEE', 'OPPOSITION'):
                            try:
                                account.balance = Decimal(FrenchTransaction.clean_amount(balance))
                            except InvalidOperation:
                                raise BrokenPageError('Unable to parse balance %r' % balance)
                            account.currency = account.get_currency(balance)
                        else:
                            account.balance = NotAvailable

            if not account.label or empty(account.balance):
                continue

            if 'CARTE_' in account._link_id:
                account.type = account.TYPE_CARD
                account.coming = account.balance
                account.balance = Decimal('0')

            yield account


class CardsList(BasePage):
    def iter_cards(self):
        for tr in self.document.getiterator('tr'):
            tds = tr.findall('td')
            if len(tds) < 4 or tds[0].attrib.get('class', '') != 'tableauIFrameEcriture1':
                continue

            yield tr.xpath('.//a')[0].attrib['href']


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(r'^CARTE \w+ RETRAIT DAB.* (?P<dd>\d{2})/(?P<mm>\d{2})( (?P<HH>\d+)H(?P<MM>\d+))? (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(r'^CARTE \w+ (?P<dd>\d{2})/(?P<mm>\d{2})( A (?P<HH>\d+)H(?P<MM>\d+))? RETRAIT DAB (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(r'^CARTE \w+ REMBT (?P<dd>\d{2})/(?P<mm>\d{2})( A (?P<HH>\d+)H(?P<MM>\d+))? (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_PAYBACK),
                (re.compile(r'^(?P<category>CARTE) \w+ (?P<dd>\d{2})/(?P<mm>\d{2}) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile(r'^(?P<dd>\d{2})(?P<mm>\d{2})/(?P<text>.*?)/?(-[\d,]+)?$'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile(r'^(?P<category>(COTISATION|PRELEVEMENT|TELEREGLEMENT|TIP)) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile(r'^(\d+ )?VIR (PERM )?POUR: (.*?) (REF: \d+ )?MOTIF: (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_TRANSFER),
                (re.compile(r'^(?P<category>VIR(EMEN)?T? \w+) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_TRANSFER),
                (re.compile(r'^(CHEQUE) (?P<text>.*)'),     FrenchTransaction.TYPE_CHECK),
                (re.compile(r'^(FRAIS) (?P<text>.*)'),      FrenchTransaction.TYPE_BANK),
                (re.compile(r'^(?P<category>ECHEANCEPRET)(?P<text>.*)'),
                                                            FrenchTransaction.TYPE_LOAN_PAYMENT),
                (re.compile(r'^(?P<category>REMISE CHEQUES)(?P<text>.*)'),
                                                            FrenchTransaction.TYPE_DEPOSIT),
                (re.compile(r'^CARTE RETRAIT (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
               ]


class AccountHistory(BasePage):
    def get_part_url(self):
        for script in self.document.getiterator('script'):
            if script.text is None:
                continue

            m = re.search('var listeEcrCavXmlUrl="(.*)";', script.text)
            if m:
                return m.group(1)

        return None

    def iter_transactions(self, coming):
        url = self.get_part_url()
        if url is None:
            # There are no transactions in this kind of account
            return

        while True:
            d = XML(self.browser.readurl(url))
            try:
                el = self.parser.select(d, '//dataBody', 1, 'xpath')
            except BrokenPageError:
                # No transactions.
                return

            s = StringIO(unicode(el.text).encode('iso-8859-1'))
            doc = self.browser.get_document(s)

            for tr in self._iter_transactions(doc, coming):
                if not tr._coming:
                    coming = False
                yield tr

            el = d.xpath('//dataHeader')[0]
            if int(el.find('suite').text) != 1:
                return

            url = urlparse(url)
            p = parse_qs(url.query)
            url = self.browser.buildurl(url.path, n10_nrowcolor=0,
                                                  operationNumberPG=el.find('operationNumber').text,
                                                  operationTypePG=el.find('operationType').text,
                                                  pageNumberPG=el.find('pageNumber').text,
                                                  idecrit=el.find('idecrit').text or '',
                                                  sign=p['sign'][0],
                                                  src=p['src'][0])

    def _iter_transactions(self, doc, coming):
        t = None
        for i, tr in enumerate(self.parser.select(doc.getroot(), 'tr')):
            try:
                raw = tr.attrib['title'].strip()
            except KeyError:
                raw = tr.xpath('./td[@headers="Libelle"]//text()')[0].strip()

            date = tr.xpath('./td[@headers="Date"]')[0].text.strip()
            if date == '':
                m = re.search('(\d+)/(\d+)', raw)
                if not m:
                    continue
                date = t.date if t else datetime.date.today()
                date = date.replace(day=int(m.group(1)), month=int(m.group(2)))
                if date <= datetime.date.today():
                    coming = False
                continue

            t = Transaction(i)
            t.parse(date=date, raw=raw)
            t.set_amount(*reversed([el.text for el in tr.xpath('./td[@class="right"]')]))
            try:
                t._coming = tr.xpath('./td[@headers="AVenir"]')[0].find('img') is not None
            except IndexError:
                t._coming = coming

            if t.label.startswith('DEBIT MENSUEL CARTE'):
                continue

            yield t
