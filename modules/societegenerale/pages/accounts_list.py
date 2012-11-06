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


from urlparse import parse_qs, urlparse
from lxml.etree import XML
from cStringIO import StringIO
from decimal import Decimal
import re

from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.browser import BrokenPageError

from .base import BasePage


__all__ = ['AccountsList', 'CardsList', 'AccountHistory']


class AccountsList(BasePage):
    LINKID_REGEXP = re.compile(".*ch4=(\w+).*")

    def on_loaded(self):
        pass

    def get_list(self):
        accounts = []
        for tr in self.document.getiterator('tr'):
            if not 'LGNTableRow' in tr.attrib.get('class', '').split():
                continue

            account = Account()
            for td in tr.getiterator('td'):
                if td.attrib.get('headers', '') == 'TypeCompte':
                    a = td.find('a')
                    account.label = unicode(a.find("span").text)
                    account._link_id = a.get('href', '')

                elif td.attrib.get('headers', '') == 'NumeroCompte':
                    id = td.text
                    id = id.replace(u'\xa0','')
                    account.id = id

                elif td.attrib.get('headers', '') == 'Libelle':
                    pass

                elif td.attrib.get('headers', '') == 'Solde':
                    balance = td.find('div').text
                    if balance != None:
                        balance = balance.replace(u'\xa0','').replace(',','.')
                        account.balance = Decimal(balance)
                    else:
                        account.balance = Decimal(0)

            if 'CARTE_' in account._link_id:
                ac = accounts[0]
                ac._card_links.append(account._link_id)
                if not ac.coming:
                    ac.coming = Decimal('0.0')
                ac.coming += account.balance
            else:
                account._card_links = []
                accounts.append(account)
        return iter(accounts)

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

        while 1:
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
        for i, tr in enumerate(self.parser.select(doc.getroot(), 'tr')):
            date = tr.xpath('./td[@headers="Date"]')[0].text.strip()
            if date == '':
                coming = False
                continue

            try:
                raw = tr.attrib['title'].strip()
            except KeyError:
                raw = tr.xpath('./td[@headers="Libelle"]//text()')[0].strip()
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
