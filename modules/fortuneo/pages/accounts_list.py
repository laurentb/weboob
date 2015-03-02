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


from lxml.html import etree
from decimal import Decimal
import re
from time import sleep

from weboob.capabilities.bank import Account, Investment
from weboob.deprecated.browser import Page, BrowserIncorrectPassword
from weboob.capabilities import NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.json import json


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(u'^(?P<category>CHEQUE)(?P<text>.*)'),        FrenchTransaction.TYPE_CHECK),
                (re.compile('^(?P<category>FACTURE CARTE) DU (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) (?P<text>.*?)( CA?R?T?E? ?\d*X*\d*)?$'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile('^(?P<category>CARTE)( DU)? (?P<dd>\d{2})/(?P<mm>\d{2}) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile('^(?P<category>(PRELEVEMENT|TELEREGLEMENT|TIP|PRLV)) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^(?P<category>ECHEANCEPRET)(?P<text>.*)'),   FrenchTransaction.TYPE_LOAN_PAYMENT),
                (re.compile('^(?P<category>RET(RAIT)? DAB) (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2})( (?P<HH>\d+)H(?P<MM>\d+))? (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^(?P<category>VIR(EMEN)?T? ((RECU|FAVEUR) TIERS|SEPA RECU)?)( /FRM)?(?P<text>.*)'),
                                                            FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^(?P<category>REMBOURST)(?P<text>.*)'),     FrenchTransaction.TYPE_PAYBACK),
                (re.compile('^(?P<category>COMMISSIONS)(?P<text>.*)'),   FrenchTransaction.TYPE_BANK),
                (re.compile('^(?P<text>(?P<category>REMUNERATION).*)'),   FrenchTransaction.TYPE_BANK),
                (re.compile('^(?P<category>REMISE CHEQUES)(?P<text>.*)'), FrenchTransaction.TYPE_DEPOSIT),
               ]


class PeaHistoryPage(Page):
    COL_LABEL = 0
    COL_UNITVALUE = 1
    COL_QUANTITY = 3
    COL_UNITPRICE = 4
    COL_VALUATION = 5
    COL_PERF = 6
    COL_WEIGHT = 7
    def get_investments(self):
        for line in self.document.xpath('//table[@id="t_intraday"]/tbody/tr'):
            if line.find_class('categorie') or line.find_class('detail') or line.find_class('detail02'):
                continue

            cols = line.findall('td')

            inv = Investment()
            inv.label = self.parser.tocleanstring(cols[self.COL_LABEL])
            link = cols[self.COL_LABEL].xpath('./a[contains(@href, "cdReferentiel")]')[0]
            inv.id = unicode(re.search('cdReferentiel=(.*)', link.attrib['href']).group(1))
            inv.code = re.match('^[A-Z]+[0-9]+(.*)$', inv.id).group(1)
            inv.quantity = self.parse_decimal(cols[self.COL_QUANTITY])
            inv.unitprice = self.parse_decimal(cols[self.COL_UNITPRICE])
            inv.unitvalue = self.parse_decimal(cols[self.COL_UNITVALUE])
            inv.valuation = self.parse_decimal(cols[self.COL_VALUATION])
            diff = cols[self.COL_PERF].text.strip()
            if diff == "-":
                inv.diff = NotAvailable
            else:
                inv.diff = Decimal(Transaction.clean_amount(diff))

            yield inv

    def parse_decimal(self, string):
        value = self.parser.tocleanstring(string)
        if value == '-':
            return NotAvailable
        return Decimal(Transaction.clean_amount(value))

    def get_operations(self, _id):
        return iter([])


class InvestmentHistoryPage(Page):
    COL_LABEL = 0
    COL_QUANTITY = 1
    COL_UNITVALUE = 2
    COL_DATE = 3
    COL_VALUATION = 4
    COL_WEIGHT = 5
    COL_UNITPRICE = 6
    COL_PERF = 7
    COL_PERF_PERCENT = 8
    def get_investments(self):
        for line in self.document.xpath('//table[@id="tableau_support"]/tbody/tr'):
            cols = line.findall('td')

            inv = Investment()
            inv.id = unicode(re.search('cdReferentiel=(.*)', cols[self.COL_LABEL].find('a').attrib['href']).group(1))
            inv.code = re.match('^[A-Z]+[0-9]+(.*)$', inv.id).group(1)
            inv.label = self.parser.tocleanstring(cols[self.COL_LABEL])
            inv.quantity = self.parse_decimal(cols[self.COL_QUANTITY])
            inv.unitprice = self.parse_decimal(cols[self.COL_UNITPRICE])
            inv.unitvalue = self.parse_decimal(cols[self.COL_UNITVALUE])
            inv.valuation = self.parse_decimal(cols[self.COL_VALUATION])
            inv.diff = self.parse_decimal(cols[self.COL_PERF])

            yield inv

    def parse_decimal(self, string):
        value = self.parser.tocleanstring(string)
        if value == '-':
            return NotAvailable
        return Decimal(Transaction.clean_amount(value))

    def get_operations(self, _id):
        return iter([])


class AccountHistoryPage(Page):
    def get_investments(self):
        return iter([])

    def get_operations(self, _id):
        """history, see http://docs.weboob.org/api/capabilities/bank.html?highlight=transaction#weboob.capabilities.bank.Transaction"""

        # TODO need to rewrite that with FrenchTransaction class http://tinyurl.com/6lq4r9t
        tables = self.document.findall(".//*[@id='tabHistoriqueOperations']/tbody/tr")

        if len(tables) == 0:
            return

        for i in range(len(tables)):
            operation = Transaction(i)
            operation.type  = 0
            operation.category  = NotAvailable

            date_oper       = tables[i].xpath("./td[2]/text()")[0]
            date_val        = tables[i].xpath("./td[3]/text()")[0]
            label           = tables[i].xpath("./td[4]/text()")[0]
            label           = re.sub(r'[ \xa0]+', ' ', label).strip()
            amount          = tables[i].xpath("./td[5]/text() | ./td[6]/text()")

            operation.parse(date=date_oper, raw=label, vdate=date_val)

            if amount[1] == u'\xa0':
                amount = amount[0]
            else:
                amount = amount[1]

            operation.set_amount(amount)

            yield operation


class AccountsList(Page):
    def on_loaded(self):
        warn = self.document.xpath('//div[@id="message_renouvellement_mot_passe"]')
        if len(warn) > 0:
            raise BrowserIncorrectPassword(warn[0].text)

        self.load_async(0)

    def load_async(self, time):
        # load content of loading divs.
        lst = self.document.xpath('//input[@type="hidden" and starts-with(@id, "asynch")]')
        if len(lst) > 0:
            params = {}
            for i, input in enumerate(lst):
                params['key%s' % i] = input.attrib['name']
                params['div%s' % i] = input.attrib['value']
            params['time'] = time

            r = self.browser.openurl(self.browser.buildurl('/AsynchAjax', **params))
            data = json.load(r)

            for i, d in enumerate(data['data']):
                div = self.document.xpath('//div[@id="%s"]' % d['key'])[0]
                html = d['flux']
                div.clear()
                div.attrib['id'] = d['key'] # needed because clear removes also all attributes
                div.insert(0, etree.fromstring(html, parser=etree.HTMLParser()))

            if 'time' in data:
                sleep(float(data['time'])/1000.0)
                return self.load_async(time)

    def need_reload(self):
        form = self.document.xpath('//form[@name="InformationsPersonnellesForm"]')
        return len(form) > 0

    ACCOUNT_TYPES = {'mes-comptes/compte-courant':    Account.TYPE_CHECKING,
                     'mes-comptes/assurance-vie':     Account.TYPE_LIFE_INSURANCE,
                     'mes-comptes/livret':            Account.TYPE_LOAN,
                    }
    def get_list(self):
        for cpt in self.document.xpath(".//*[@class='synthese_id_compte']"):
            account = Account()

            # account.id
            account.id = cpt.xpath("./span[1]/text()")[0].replace(u"\xa0", "").replace(',', '.').replace("EUR", "").replace("\n", "").replace("\t", "").replace(u"\xb0", '').replace(" ", "").replace('N', '')

            # account balance
            account.balance = Decimal(Transaction.clean_amount(cpt.xpath("./span[2]/text()")[0]))
            account.currency = account.get_currency(cpt.xpath("./span[2]/text()")[0])

            # account coming TODO
            #mycomingval = cpt.xpath("../../following-sibling::*[1]/td[2]/a[@class='lien_synthese_encours']/span/text()")[0].replace(',', '.').replace("EUR", "").replace("\n", "").replace("\t", "").replace(u"\xa0", "")
            #mycomingval = cpt.xpath("../../following-sibling::*[1]/td[2]")[0]
            #mycomingval = cpt.xpath("./../../../a[@class='lien_synthese_encours']/span[@class='synthese_encours']/text()")[0].replace(',', '.').replace("EUR", "").replace("\n", "").replace("\t", "").replace(u"\xa0", "")

            #if mycomingval == '-':
            #    account.coming = Decimal(0)
            #else:
            #    account.coming = Decimal(mycomingval)

            url_to_parse = cpt.xpath('@href')[0].replace("\n", "")  # link

            # account._link_id = lien vers historique d'un compte (courant of livret)
            if '/mes-comptes/livret/' in url_to_parse:
                compte_id_re = re.compile(r'.*\?(.*)$')
                account._link_id = '/fr/prive/mes-comptes/livret/consulter-situation/consulter-solde.jsp?%s' % \
                    (compte_id_re.search(url_to_parse).groups()[0])
            else:
                account._link_id = url_to_parse

            # account.label
            account.label = cpt.xpath('./text()')[1].replace(u'-\xa0', '').replace("\n", "").replace("\t", "")

            for pattern, type in self.ACCOUNT_TYPES.iteritems():
                if pattern in account._link_id:
                    account.type = type

            yield account


class GlobalAccountsList(Page):
    pass

# vim:ts=4:sw=4
