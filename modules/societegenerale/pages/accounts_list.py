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


import urllib
import datetime
from urlparse import parse_qs, urlparse
from lxml.etree import XML
from cStringIO import StringIO
from decimal import Decimal, InvalidOperation
import re

from weboob.capabilities.base import empty, NotAvailable
from weboob.capabilities.bank import Account, Investment
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.deprecated.browser import BrokenPageError
from weboob.browser.filters.standard import CleanText

from .base import BasePage


class AccountsList(BasePage):
    LINKID_REGEXP = re.compile(".*ch4=(\w+).*")

    def on_loaded(self):
        pass

    TYPES = {u'Compte Bancaire':     Account.TYPE_CHECKING,
             u'Compte Epargne':      Account.TYPE_SAVINGS,
             u'Compte Sur Livret':   Account.TYPE_SAVINGS,
             u'Compte Titres':       Account.TYPE_MARKET,
             u'Crédit':              Account.TYPE_LOAN,
             u'Ldd':                 Account.TYPE_SAVINGS,
             u'Livret':              Account.TYPE_SAVINGS,
             u'PEA':                 Account.TYPE_SAVINGS,
             u'PEL':                 Account.TYPE_SAVINGS,
             u'Plan Epargne':        Account.TYPE_SAVINGS,
             u'Prêt':                Account.TYPE_LOAN,
            }

    def get_list(self):
        def check_valid_url(url):
            pattern = ['/restitution/cns_detailAVPAT.html',
                       '/restitution/cns_detailPea.html',
                       '/restitution/cns_detailAlterna.html',
                      ]

            for p in pattern:
                if url.startswith(p):
                    return False
            return True

        for tr in self.document.getiterator('tr'):
            if 'LGNTableRow' not in tr.attrib.get('class', '').split():
                continue

            account = Account()
            for td in tr.getiterator('td'):
                if td.attrib.get('headers', '') == 'TypeCompte':
                    a = td.find('a')
                    if a is None:
                        break
                    account.label = self.parser.tocleanstring(a)
                    account._link_id = a.get('href', '')
                    for pattern, actype in self.TYPES.iteritems():
                        if account.label.startswith(pattern):
                            account.type = actype
                            break
                    else:
                        if account._link_id.startswith('/asv/asvcns10.html'):
                            account.type = Account.TYPE_LIFE_INSURANCE
                    # Website crashes when going on theses URLs
                    if not check_valid_url(account._link_id):
                        account._link_id = None

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

            if account._link_id and 'CARTE_' in account._link_id:
                account.type = account.TYPE_CARD

            if account.type == Account.TYPE_UNKNOWN:
                self.logger.debug('Unknown account type: %s', account.label)

            yield account


class CardsList(BasePage):
    def iter_cards(self):
        for tr in self.document.getiterator('tr'):
            tds = tr.findall('td')
            if len(tds) < 4 or tds[0].attrib.get('class', '') != 'tableauIFrameEcriture1':
                continue

            yield tr.xpath('.//a')[0].attrib['href']


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(r'^CARTE \w+ RETRAIT DAB.*? (?P<dd>\d{2})/(?P<mm>\d{2})( (?P<HH>\d+)H(?P<MM>\d+))? (?P<text>.*)'),
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
    debit_date =  None
    def get_part_url(self):
        for script in self.document.getiterator('script'):
            if script.text is None:
                continue

            m = re.search('var listeEcrCavXmlUrl="(.*)";', script.text)
            if m:
                return m.group(1)

        return None

    def iter_transactions(self):
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

            for tr in self._iter_transactions(doc):
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

    def _iter_transactions(self, doc):
        t = None
        for i, tr in enumerate(self.parser.select(doc.getroot(), 'tr')):
            try:
                raw = tr.attrib['title'].strip()
            except KeyError:
                raw = tr.xpath('./td[@headers="Libelle"]//text()')[0].strip()

            date = tr.xpath('./td[@headers="Date"]')[0].text.strip()
            if date == '':
                m = re.search(r'(\d+)/(\d+)', raw)
                if not m:
                    continue
                self.debit_date = t.date if t else datetime.date.today()
                self.debit_date = self.debit_date.replace(day=int(m.group(1)), month=int(m.group(2)))
                if not t:
                    continue

            t = Transaction()

            if 'EnTraitement' in tr.get('class', ''):
                t._coming = True
            else:
                t._coming = False

            t.set_amount(*reversed([el.text for el in tr.xpath('./td[@class="right"]')]))
            if date == '':
                # Credit from main account.
                t.amount = -t.amount
                date = self.debit_date
            t.rdate = t.parse_date(date)
            t.parse(raw=raw, date=(self.debit_date or date))

            yield t

    def get_iban(self):
        return CleanText().filter(self.document.xpath("//font[contains(text(),'IBAN')]/b[1]")[0]).replace(' ', '')


class Invest(object):
    def create_investement(self, cells):
        inv = Investment()
        inv.quantity = self.parse_decimal(cells[self.COL_QUANTITY])
        inv.unitvalue = self.parse_decimal(cells[self.COL_UNITVALUE])
        inv.unitprice = NotAvailable
        inv.valuation = self.parse_decimal(cells[self.COL_VALUATION])
        inv.diff = NotAvailable

        link = cells[self.COL_LABEL].xpath('a[contains(@href, "CDCVAL=")]')[0]
        m = re.search('CDCVAL=([^&]+)', link.attrib['href'])
        if m:
            inv.code = m.group(1)
        else:
            inv.code = NotAvailable
        return inv


class Market(BasePage, Invest):
    COL_LABEL = 0
    COL_QUANTITY = 1
    COL_UNITVALUE = 2
    COL_VALUATION = 3
    COL_DIFF = 4

    def iter_investment(self):
        doc = self.browser.get_document(self.browser.openurl('/brs/fisc/fisca10a.html'), encoding='utf-8')
        num_page = None
        try:
            num_page = int(self.parser.tocleanstring(doc.xpath(u'.//tr[contains(td[1], "Relevé des plus ou moins values latentes")]/td[2]')[0]).split('/')[1])
        except IndexError:
            pass
        docs = [doc]
        if num_page:
            for n in range(2, num_page + 1):
                docs.append(self.browser.get_document(self.browser.openurl('%s%s' % ('/brs/fisc/fisca10a.html?action=12&numPage=', str(n))), encoding='utf-8'))

        for doc in docs:
            for tr in doc.xpath('//tr[count(td)=6 and td[1]/strong]'):
                cells = tr.findall('td')

                inv = Investment()
                inv.label = unicode(cells[self.COL_LABEL].xpath('.//span')[0].attrib['title'].split(' - ')[0])
                inv.code = unicode(cells[self.COL_LABEL].xpath('.//span')[0].attrib['title'].split(' - ')[1])
                inv.quantity = self.parse_decimal(cells[self.COL_QUANTITY])
                inv.unitprice = self.parse_decimal(tr.xpath('./following-sibling::tr/td[3]')[0])
                inv.unitvalue = self.parse_decimal(cells[self.COL_UNITVALUE])
                inv.valuation = self.parse_decimal(cells[self.COL_VALUATION])
                inv.diff = self.parse_decimal(cells[self.COL_DIFF])

                yield inv


class LifeInsurance(BasePage):
    def get_error(self):
        try:
            return self.document.xpath("//div[@class='net2g_asv_error_full_page']")[0].text.strip()
        except IndexError:
            return super(LifeInsurance, self).get_error()


class LifeInsuranceInvest(LifeInsurance, Invest):
    COL_LABEL = 0
    COL_QUANTITY = 1
    COL_UNITVALUE = 2
    COL_VALUATION = 3

    def iter_investment(self):
        for tr in self.document.xpath("//table/tbody/tr[starts-with(@class, 'net2g_asv_tableau_ligne_')]"):
            cells = tr.findall('td')

            inv = self.create_investement(cells)
            inv.label = cells[self.COL_LABEL].xpath('a/span')[0].text.strip()
            inv.description = cells[self.COL_LABEL].xpath('a//div/b[last()]')[0].tail

            yield inv


class LifeInsuranceHistory(LifeInsurance):
    COL_DATE = 0
    COL_LABEL = 1
    COL_AMOUNT = 2
    COL_STATUS = 3

    def iter_transactions(self):
        for tr in self.document.xpath("//table/tbody/tr[starts-with(@class, 'net2g_asv_tableau_ligne_')]"):
            cells = tr.findall('td')

            link = cells[self.COL_LABEL].xpath('a')[0]
            # javascript:detailOperation('operationForm', '2');
            m = re.search(", '([0-9]+)'", link.attrib['href'])
            if m:
                id_trans = m.group(1)
            else:
                id_trans = ''

            trans = Transaction()
            trans._temp_id = id_trans
            trans.parse(raw=link.attrib['title'], date=cells[self.COL_DATE].text)
            trans.set_amount(cells[self.COL_AMOUNT].text)
            # search for 'Réalisé'
            trans._coming = 'alis' not in cells[self.COL_STATUS].text.strip()

            self.set_date(trans)

            yield trans

    def set_date(self, trans):
        """fetch date and vdate from another page"""
        form = self.document.xpath('//form[@id="operationForm"]')[0]

        # go to the page containing the dates
        data = dict((item.name, item.value or '') for item in form.inputs)
        data['a100_asv_action'] = 'detail'
        data['a100_asv_indexOp'] = trans._temp_id
        doc = self.browser.get_document(self.browser.openurl('/asv/AVI/asvcns21c.html', urllib.urlencode(data)), encoding='utf-8')

        # process the data
        date_xpath = '//td[@class="net2g_asv_suiviOperation_element1"]/following-sibling::td'
        vdate_xpath = '//td[@class="net2g_asv_tableau_cell_date"]'
        trans.date = self.parse_date(doc, trans, date_xpath, 1)
        trans.vdate = self.parse_date(doc, trans, vdate_xpath, 0)

    @staticmethod
    def parse_date(doc, trans, xpath, index):
        elem = doc.xpath(xpath)[index]
        if elem.text:
            return trans.parse_date(elem.text.strip())
        else:
            return NotAvailable


class ListRibPage(BasePage):
    def get_rib_url(self, account):
        for div in self.document.xpath('//table//td[@class="fond_cellule"]//div[@class="tableauBodyEcriture1"]//table//tr'):
            if account.id == CleanText().filter(div.xpath('./td[2]//div/div')).replace(' ', ''):
                href = CleanText().filter(div.xpath('./td[4]//a/@href'))
                m = re.search("javascript:windowOpenerRib\('(.*?)'(.*)\)", href)
                if m:
                    return m.group(1)
