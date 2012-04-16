# -*- coding: utf-8 -*-

# Copyright(C) 2012 Gilles-Alexandre Quenot
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

# AccountsList, IndexPage
from urlparse import parse_qs, urlparse
from lxml.etree import XML
from cStringIO import StringIO
from decimal import Decimal
import re

from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.browser import BasePage, BrokenPageError


#__all__ = ['IndexPage', 'AccountsList', 'AccountHistory']
__all__ = ['AccountHistory']


#class IndexPage(BasePage):
#    def on_loaded(self):
#    	pass
#
#    def get_list(self):
#        l = []
#        account.label = "test"
#        account.id = "Livret +"
#        account.balance = "20"
#        account._link_id = "https://www.fortuneo.fr/fr/prive/default.jsp?ANav=1"
#        l.append(account)
#        return l

#class AccountsList(BasePage):
#    def on_loaded(self):
#        pass
#
#    def get_list(self):
#	#print "DEBUG self.document="+self.document
#        account = []
#        account.append('test')
#        account.append('Livret +')
#        account.append('20')
#        account.append('https://www.fortuneo.fr/fr/prive/default.jsp?ANav=1')
#	return account
#        #account.append(account)
#        #for el in self.document.xpath('//table[@id="tableauComptesTitEtCotit"]/tbody/'):
#        #l.append(account)
#        ##for tr in self.document.getiterator('tr'):
#        ##    if 'LGNTableRow' in tr.attrib.get('class', '').split():
#        ##        account = Account()
#        ##        for td in tr.getiterator('td'):
#        ##            if td.attrib.get('headers', '') == 'TypeCompte':
#        ##                a = td.find('a')
#        ##                account.label = unicode(a.find("span").text)
#        ##                account._link_id = a.get('href', '')
#
#        ##            elif td.attrib.get('headers', '') == 'NumeroCompte':
#        ##                id = td.text
#        ##                id = id.replace(u'\xa0','')
#        ##                account.id = id
#
#        ##            elif td.attrib.get('headers', '') == 'Libelle':
#        ##                pass
#
#        ##            elif td.attrib.get('headers', '') == 'Solde':
#        ##                balance = td.find('div').text
#        ##                if balance != None:
#        ##                    balance = balance.replace(u'\xa0','').replace(',','.')
#        ##                    account.balance = Decimal(balance)
#        ##                else:
#        ##                    account.balance = Decimal(0)
#
#        ##        l.append(account)
#
#        #return l

#class Transaction(FrenchTransaction):
#    pass
    #PATTERNS = [(re.compile(r'^CARTE \w+ RETRAIT DAB.* (?P<dd>\d{2})/(?P<mm>\d{2}) (?P<HH>\d+)H(?P<MM>\d+) (?P<text>.*)'),
    #                                                        FrenchTransaction.TYPE_WITHDRAWAL),
    #            (re.compile(r'^(?P<category>CARTE) \w+ (?P<dd>\d{2})/(?P<mm>\d{2}) (?P<text>.*)'),
    #                                                        FrenchTransaction.TYPE_CARD),
    #            (re.compile(r'^(?P<category>(COTISATION|PRELEVEMENT|TELEREGLEMENT|TIP)) (?P<text>.*)'),
    #                                                        FrenchTransaction.TYPE_ORDER),
    #            (re.compile(r'^(?P<category>VIR(EMEN)?T? \w+) (?P<text>.*)'),
    #                                                        FrenchTransaction.TYPE_TRANSFER),
    #            (re.compile(r'^(CHEQUE) (?P<text>.*)'),     FrenchTransaction.TYPE_CHECK),
    #            (re.compile(r'^(FRAIS) (?P<text>.*)'),      FrenchTransaction.TYPE_BANK),
    #            (re.compile(r'^(?P<category>ECHEANCEPRET)(?P<text>.*)'),
    #                                                        FrenchTransaction.TYPE_LOAN_PAYMENT),
    #            (re.compile(r'^(?P<category>REMISE CHEQUES)(?P<text>.*)'),
    #                                                        FrenchTransaction.TYPE_DEPOSIT),
    #           ]

class AccountHistory(BasePage):
    get_list = [1, 2, 3, 4]
    def get_part_url(self):
        print "DEBUG AccountHistory.get_part_url a implementer"
        pass
        #for script in self.document.getiterator('script'):
        #    if script.text is None:
        #        continue

        #    m = re.search('var listeEcrCavXmlUrl="(.*)";', script.text)
        #    if m:
        #        return m.group(1)

        #raise BrokenPageError('Unable to find link to history part')

    #def iter_transactions(self):
    #    print "DEBUG iter_transactions a implementer"
    #    pass
    #    #url = self.get_part_url()
    #    #while 1:
    #    #    d = XML(self.browser.readurl(url))
    #    #    el = d.xpath('//dataBody')[0]
    #    #    s = StringIO(el.text)
    #    #    doc = self.browser.get_document(s)

    #    #    for tr in self._iter_transactions(doc):
    #    #        yield tr

    #    #    el = d.xpath('//dataHeader')[0]
    #    #    if int(el.find('suite').text) != 1:
    #    #        return

    #    #    url = urlparse(url)
    #    #    p = parse_qs(url.query)
    #    #    url = self.browser.buildurl(url.path, n10_nrowcolor=0,
    #    #                                          operationNumberPG=el.find('operationNumber').text,
    #    #                                          operationTypePG=el.find('operationType').text,
    #    #                                          pageNumberPG=el.find('pageNumber').text,
    #    #                                          sign=p['sign'][0],
    #    #                                          src=p['src'][0])


    def _iter_transactions(self, doc):
        print "DEBUG _iter_transactions a implementer"
        pass
        #for i, tr in enumerate(self.parser.select(doc.getroot(), 'tr')):
        #    t = Transaction(i)
        #    t.parse(date=tr.xpath('./td[@headers="Date"]')[0].text,
        #            raw=tr.attrib['title'].strip())
        #    t.set_amount(*reversed([el.text for el in tr.xpath('./td[@class="right"]')]))
        #    t._coming = tr.xpath('./td[@headers="AVenir"]')[0].text
        #    yield t
