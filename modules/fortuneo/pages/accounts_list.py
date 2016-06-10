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
from datetime import date
from dateutil.relativedelta import relativedelta

from mechanize import FormNotFoundError

from weboob.browser.filters.standard import CleanText
from weboob.capabilities import NotAvailable
from weboob.capabilities.bank import Account, Investment
from weboob.deprecated.browser import Page, BrowserIncorrectPassword
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
        value = Transaction.clean_amount(self.parser.tocleanstring(string))
        if value == '-':
            return NotAvailable
        return Decimal(value)

    def select_period(self):
        return True

    def get_operations(self, account):
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

    def select_period(self):
        self.browser.location(self.url.replace('portefeuille-assurance-vie.jsp', 'operations/assurance-vie-operations.jsp'))

        try:
            self.browser.select_form(name='OperationsForm')
        except FormNotFoundError:
            return False
        self.browser.set_all_readonly(False)
        self.browser['dateDebut'] = (date.today() - relativedelta(years=1)).strftime('%d/%m/%Y')
        self.browser['nbrEltsParPage'] = '100'
        self.browser.submit()
        return True

    def get_operations(self, account):
        for tr in self.document.xpath('//table[@id="tableau_histo_opes"]/tbody/tr'):
            tds = tr.findall('td')

            t = Transaction()
            t.parse(date=self.parser.tocleanstring(tds[1]),
                    raw=self.parser.tocleanstring(tds[2]))
            t.set_amount(self.parser.tocleanstring(tds[-1]))
            yield t


class AccountHistoryPage(Page):
    def get_investments(self):
        return iter([])

    def select_period(self):
        self.browser.select_form(name='ConsultationHistoriqueOperationsForm')
        self.browser.set_all_readonly(False)
        self.browser['dateRechercheDebut'] = (date.today() - relativedelta(years=1)).strftime('%d/%m/%Y')
        self.browser['nbrEltsParPage'] = '100'
        self.browser.submit()

        return True


    def get_operations(self, account):
        """history, see http://docs.weboob.org/api/capabilities/bank.html?highlight=transaction#weboob.capabilities.bank.Transaction"""

        # TODO need to rewrite that with FrenchTransaction class http://tinyurl.com/6lq4r9t
        tables = self.document.findall(".//*[@id='tabHistoriqueOperations']/tbody/tr")

        if len(tables) == 0:
            return

        for i in range(len(tables)):
            operation = Transaction()
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


class CardHistoryPage(Page):
    def get_investments(self):
        return iter([])

    def select_period(self):
        return True

    def get_operations(self, account):
        for op in self.document.xpath('//table[@id="tableauEncours"]/tbody/tr'):
            rdate =  self.parser.tocleanstring(op.xpath('./td[1]')[0])
            date =   self.parser.tocleanstring(op.xpath('./td[2]')[0])
            raw =    self.parser.tocleanstring(op.xpath('./td[3]')[0])
            credit = self.parser.tocleanstring(op.xpath('./td[4]')[0])
            debit =  self.parser.tocleanstring(op.xpath('./td[5]')[0])

            tr = Transaction()
            tr.parse(date=date, raw=raw)
            tr.rdate = tr.parse_date(rdate)
            tr.type = tr.TYPE_CARD
            tr.set_amount(credit, debit)
            yield tr


class AccountsList(Page):
    def on_loaded(self):
        warn = self.document.xpath('//div[@id="message_renouvellement_mot_passe"] | \
                                    //span[contains(text(), "Votre identifiant change")] | \
                                    //span[contains(text(), "Nouveau mot de passe")] | \
                                    //span[contains(text(), "Renouvellement de votre mot de passe")]')
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

    def need_sms(self):
        return len(self.document.xpath('//div[@id="aidesecuforte"]'))

    ACCOUNT_TYPES = {'mes-comptes/compte-courant/consulter-situation': Account.TYPE_CHECKING,
                     'mes-comptes/compte-courant/carte-bancaire':      Account.TYPE_CARD,
                     'mes-comptes/assurance-vie':                      Account.TYPE_LIFE_INSURANCE,
                     'mes-comptes/livret':                             Account.TYPE_SAVINGS,
                     'mes-comptes/pea':                                Account.TYPE_MARKET,
                     'mes-comptes/compte-titres':                      Account.TYPE_MARKET,
                    }
    def get_list(self):
        account = None

        for cpt in self.document.xpath('//a[@class="synthese_id_compte" or @class="synthese_carte_differe"]'):
            url_to_parse = cpt.xpath('@href')[0].replace("\n", "")  # link
            # account._link_id = lien vers historique d'un compte (courant ou livret)
            if '/mes-comptes/livret/' in url_to_parse:
                compte_id_re = re.compile(r'.*\?(.*)$')
                link_id = '/fr/prive/mes-comptes/livret/consulter-situation/consulter-solde.jsp?%s' % \
                    (compte_id_re.search(url_to_parse).groups()[0])
            else:
                link_id = url_to_parse

            number = cpt.xpath('./span[@class="synthese_numero_compte"]')
            if len(number) == 0:
                account._card_links.append(link_id)
                continue

            account = Account()
            account.id = self.parser.tocleanstring(number[0]).replace(u'N°', '')

            try:
                balance = self.parser.tocleanstring(cpt.xpath('./span[contains(@class, "synthese_solde")]')[0])
            except IndexError:
                continue

            account.balance = Decimal(Transaction.clean_amount(balance))
            account.currency = account.get_currency(balance)
            account._link_id = link_id
            account._card_links = []
            account.label = (' '.join([CleanText.clean(part) for part in cpt.xpath('./text()')])).strip(' - ').strip()

            for pattern, type in self.ACCOUNT_TYPES.iteritems():
                if pattern in account._link_id:
                    account.type = type

            yield account


class GlobalAccountsList(Page):
    pass
