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

from urllib import urlencode
import re
from time import sleep
from datetime import date

from dateutil.relativedelta import relativedelta
from lxml.html import etree

from weboob.browser.filters.html import Link
from weboob.browser.filters.standard import CleanText, CleanDecimal, RawText
from weboob.capabilities import NotAvailable
from weboob.capabilities.bank import Account, Investment
from weboob.browser.pages import HTMLPage, LoggedPage, FormNotFound
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.json import json
from weboob.exceptions import ActionNeeded, BrowserUnavailable


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


class PeaHistoryPage(LoggedPage, HTMLPage):
    COL_LABEL = 0
    COL_UNITVALUE = 1
    COL_QUANTITY = 3
    COL_UNITPRICE = 4
    COL_VALUATION = 5
    COL_PERF = 6
    COL_WEIGHT = 7

    def get_investments(self, account):
        if account is not None:
            # the balance is highly dynamic, fetch it along with the investments to grab a snapshot
            account.balance = CleanDecimal(None, replace_dots=True).filter(self.get_balance(account.type))

        for line in self.doc.xpath('//table[@id="t_intraday"]/tbody/tr'):
            if line.find_class('categorie') or line.find_class('detail') or line.find_class('detail02'):
                continue

            cols = line.findall('td')

            inv = Investment()
            inv.label = CleanText(None).filter(cols[self.COL_LABEL])
            link = cols[self.COL_LABEL].xpath('./a[contains(@href, "cdReferentiel")]')[0]
            inv.id = unicode(re.search('cdReferentiel=(.*)', link.attrib['href']).group(1))
            inv.code = re.match('^[A-Z]+[0-9]+(.*)$', inv.id).group(1)
            inv.quantity = self.parse_decimal(cols[self.COL_QUANTITY], True)
            inv.unitprice = self.parse_decimal(cols[self.COL_UNITPRICE], True)
            inv.unitvalue = self.parse_decimal(cols[self.COL_UNITVALUE], False)
            inv.valuation = self.parse_decimal(cols[self.COL_VALUATION], True)
            diff = cols[self.COL_PERF].text.strip()
            if diff == "-":
                inv.diff = NotAvailable
            else:
                inv.diff = CleanDecimal(None, replace_dots=True).filter(diff)

            yield inv

    def parse_decimal(self, string, replace_dots):
        string = CleanText(None).filter(string)
        if string == '-':
            return NotAvailable
        return CleanDecimal(None, replace_dots=replace_dots, default=NotAvailable).filter(string)

    def select_period(self):
        try:
            form = self.browser.page.get_form(name='form_historique_titres')
        except FormNotFound:
            return False
        form['dateDebut'] = (date.today() - relativedelta(years=2)).strftime('%d/%m/%Y')
        form['nbResultats'] = '100'
        form.submit()
        return True

    def get_operations(self, account):
        for tr in self.doc.xpath('//table[@id="tabHistoriqueOperations"]/tbody/tr'):
            tds = tr.findall('td')
            if len(CleanText(None).filter(tds[-1])) == 0:
                continue
            t = Transaction()
            t.type = Transaction.TYPE_BANK
            t.parse(date=CleanText(None).filter(tds[3]),
                    raw=CleanText(None).filter(tds[1]))
            t.amount = CleanDecimal(None, replace_dots=True, default=0).filter(tds[-2])
            t.commission = CleanDecimal(None, replace_dots=True, default=0).filter(tds[-3])
            investment = Investment()
            investment.label = CleanText(None).filter(tds[0])
            investment.quantity = CleanDecimal(None, replace_dots=True, default=0).filter(tds[4])
            investment.unitvalue = CleanDecimal(None, replace_dots=True, default=0).filter(tds[5])
            t.investments = [investment]
            yield t

    def get_balance(self, account_type):
        raw_balance = None
        for tr in self.doc.xpath('//div[@id="valorisation_compte"]//table/tr'):
            if account_type == Account.TYPE_MARKET:
                if u'Évaluation Titres' in CleanText('.')(tr):
                    raw_balance = RawText('./td[2]')(tr)
                    break
            elif 'Valorisation totale' in CleanText('.')(tr):
                raw_balance = RawText('./td[2]')(tr)
        return raw_balance

    def get_currency(self):
        return Account.get_currency(CleanText('//div[@id="valorisation_compte"]//td[contains(text(), "Solde")]')(self.doc))


class InvestmentHistoryPage(LoggedPage, HTMLPage):
    COL_LABEL = 0
    COL_QUANTITY = 1
    COL_UNITVALUE = 2
    COL_DATE = 3
    COL_VALUATION = 4
    COL_WEIGHT = 5
    COL_UNITPRICE = 6
    COL_PERF = 7
    COL_PERF_PERCENT = 8

    def get_investments(self, account):
        for line in self.doc.xpath('//table[@id="tableau_support"]/tbody/tr'):
            cols = line.findall('td')

            inv = Investment()
            inv.id = unicode(re.search('cdReferentiel=(.*)', cols[self.COL_LABEL].find('a').attrib['href']).group(1))
            inv.code = re.match('^[A-Z]+[0-9]+(.*)$', inv.id).group(1)
            inv.label = CleanText(None).filter(cols[self.COL_LABEL])
            inv.quantity = self.parse_decimal(cols[self.COL_QUANTITY])
            inv.unitprice = self.parse_decimal(cols[self.COL_UNITPRICE])
            inv.unitvalue = self.parse_decimal(cols[self.COL_UNITVALUE])
            inv.valuation = self.parse_decimal(cols[self.COL_VALUATION])
            inv.diff = self.parse_decimal(cols[self.COL_PERF])

            yield inv

    def parse_decimal(self, string):
        string = CleanText(None).filter(string)
        if string == '-':
            return NotAvailable
        return CleanDecimal(None, replace_dots=True).filter(string)

    def select_period(self):
        assert isinstance(self.browser.page, type(self))

        try:
            form = self.browser.page.get_form(name='OperationsForm')
        except FormNotFound:
            return False

        form['dateDebut'] = (date.today() - relativedelta(years=2)).strftime('%d/%m/%Y')
        form['nbrEltsParPage'] = '100'
        form.submit()
        return True

    def get_operations(self, account):
        for tr in self.doc.xpath('//table[@id="tableau_histo_opes"]/tbody/tr'):
            tds = tr.findall('td')
            if len(CleanText(None).filter(tds[-1])) == 0:
                continue
            t = Transaction()
            t.type = Transaction.TYPE_BANK
            t.parse(date=CleanText(None).filter(tds[1]),
                    raw=CleanText(None).filter(tds[2]))
            t.amount = CleanDecimal(None, replace_dots=True, default=0).filter(tds[-1])
            yield t

    def get_balance(self, account_type):
        for div in self.doc.xpath('//div[@class="block synthese_vie"]/div/div/div'):
            if 'Valorisation' in CleanText('.')(div):
                return RawText('./p/strong')(div)

class AccountHistoryPage(LoggedPage, HTMLPage):
    def build_doc(self, content):
        content = re.sub(br'\*<E040032TC MSBILL.INFO', b'*', content)
        return super(AccountHistoryPage, self).build_doc(content)

    def get_balance(self):
        for tr in self.doc.xpath('//table[@id="tableauConsultationHisto"]/tbody/tr'):
            if 'Solde' in CleanText('./td')(tr):
                return CleanText('./td/strong')(tr)

    def get_investments(self, account):
        return iter([])

    def select_period(self):
        # form = self.get_form(name='ConsultationHistoriqueOperationsForm')
        form = self.get_form(xpath='//form[@name="ConsultationHistoriqueOperationsForm" '
                                   ' or @name="form_historique_titres" '
                                   ' or @name="OperationsForm"]')

        form['dateRechercheDebut'] = (date.today() - relativedelta(years=2)).strftime('%d/%m/%Y')
        form['nbrEltsParPage'] = '100'
        form.submit()

        return True

    def get_operations(self, account):
        """history, see http://docs.weboob.org/api/capabilities/bank.html?highlight=transaction#weboob.capabilities.bank.Transaction"""

        # TODO need to rewrite that with FrenchTransaction class http://tinyurl.com/6lq4r9t
        tables = self.doc.findall(".//*[@id='tabHistoriqueOperations']/tbody/tr")

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

            operation.amount = CleanDecimal(None).filter(amount)

            yield operation


class CardHistoryPage(LoggedPage, HTMLPage):
    def get_investments(self, account):
        return iter([])

    def select_period(self):
        return True

    def get_operations(self, account):
        cleaner = CleanText(None).filter
        for op in self.doc.xpath('//table[@id="tableauEncours"]/tbody/tr'):
            rdate =  cleaner(op.xpath('./td[1]')[0])
            date =   cleaner(op.xpath('./td[2]')[0])
            raw =    cleaner(op.xpath('./td[3]')[0])
            credit = cleaner(op.xpath('./td[4]')[0])
            debit =  cleaner(op.xpath('./td[5]')[0])

            tr = Transaction()
            tr.parse(date=date, raw=raw)
            tr.rdate = tr.parse_date(rdate)
            tr.type = tr.TYPE_CARD
            if credit:
                tr.amount = CleanDecimal(None, replace_dots=True).filter(credit)
            elif debit:
                tr.amount = -abs(CleanDecimal(None, replace_dots=True).filter(debit))
            yield tr


class AccountsList(LoggedPage, HTMLPage):
    def on_load(self):
        warn = self.doc.xpath(u'//div[@id="message_renouvellement_mot_passe"] | \
                               //span[contains(text(), "Votre identifiant change")] | \
                               //span[contains(text(), "Nouveau mot de passe")] | \
                               //span[contains(text(), "Renouvellement de votre mot de passe")] |\
                               //span[contains(text(), "Mieux vous connaître")]')
        if len(warn) > 0:
            raise ActionNeeded(warn[0].text)

    def load_async(self, time):
        total = 0
        restart = True
        while restart:
            restart = False

            # load content of loading divs.
            lst = self.doc.xpath('//input[@type="hidden" and starts-with(@id, "asynch")]')
            if len(lst) > 0:
                params = {}
                for i, input in enumerate(lst):
                    params['key%s' % i] = input.attrib['name']
                    params['div%s' % i] = input.attrib['value']
                params['time'] = time

                r = self.browser.open('/AsynchAjax?%s' % urlencode(params))
                data = json.loads(r.content)

                for i, d in enumerate(data['data']):
                    div = self.doc.xpath('//div[@id="%s"]' % d['key'])[0]
                    html = d['flux']
                    div.clear()
                    div.attrib['id'] = d['key'] # needed because clear removes also all attributes
                    div.insert(0, etree.fromstring(html, parser=etree.HTMLParser()))

                if 'time' in data:
                    wait = float(data['time'])/1000.0
                    self.logger.debug('should wait %f more seconds', wait)
                    total += wait
                    if total > 120:
                        raise BrowserUnavailable('too long time to wait')

                    sleep(wait)
                    restart = True

    def need_reload(self):
        form = self.doc.xpath('//form[@name="InformationsPersonnellesForm"]')
        return len(form) > 0

    def need_sms(self):
        return len(self.doc.xpath('//div[@id="aidesecuforte"]'))

    ACCOUNT_TYPES = {'mes-comptes/compte-courant/consulter-situation': Account.TYPE_CHECKING,
                     'mes-comptes/compte-especes':                     Account.TYPE_SAVINGS,
                     'mes-comptes/compte-courant/carte-bancaire':      Account.TYPE_CARD,
                     'mes-comptes/assurance-vie':                      Account.TYPE_LIFE_INSURANCE,
                     'mes-comptes/livret':                             Account.TYPE_SAVINGS,
                     'mes-comptes/pea':                                Account.TYPE_PEA,
                     'mes-comptes/ppe':                                Account.TYPE_PEA,
                     'mes-comptes/compte-titres-pea':                  Account.TYPE_MARKET
                    }

    def get_list(self):
        accounts = []
        account = None

        for cpt in self.doc.xpath('//div[contains(@class, " compte") and not(contains(@class, "compte_selected"))]'):
            account = Account()
            account._history_link = Link('./ul/li/a[contains(@id, "consulter_solde") '
                                         'or contains(@id, "historique")'
                                         'or contains(@id, "assurance_vie_operations")]')(cpt)

            number = RawText('./a[contains(@class, "numero_compte")]')(cpt).replace(u'N° ', '')

            account.id = CleanText(None).filter(number).replace(u'N°', '')

            account._card_links = []
            card_link = Link('./ul/li/a[contains(text(), "Carte bancaire")]', default='')(cpt)
            if len(card_link) > 0:
                account._card_links.append(card_link)

            account.label = CleanText('./a[contains(@class, "numero_compte")]/@title')(cpt)

            for pattern, type in self.ACCOUNT_TYPES.iteritems():
                if pattern in account._history_link:
                    account.type = type
                    break

            if account.type in {Account.TYPE_PEA, Account.TYPE_MARKET, Account.TYPE_LIFE_INSURANCE}:
                account._investment_link = Link('./ul/li/a[contains(@id, "portefeuille")]')(cpt)
                balance = self.browser.open(account._investment_link).page.get_balance(account.type)
            else:
                balance = self.browser.open(account._history_link).page.get_balance()

            if account.type in {Account.TYPE_PEA, Account.TYPE_MARKET}:
                account.currency = self.browser.open(account._investment_link).page.get_currency()
            else:
                account.currency = account.get_currency(balance)
            account.balance = CleanDecimal(None, replace_dots=True).filter(balance)

            if account.type in (Account.TYPE_CHECKING, Account.TYPE_SAVINGS):
                # Need a token sent by SMS to customers
                account.iban = NotAvailable

            if (account.label, account.id, account.balance) not in [(a.label, a.id, a.balance) for a in accounts]:
                accounts.append(account)

        return iter(accounts)


class GlobalAccountsList(LoggedPage, HTMLPage):
    pass
