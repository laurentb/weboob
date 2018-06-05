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

from __future__ import unicode_literals

import re
from time import sleep
from datetime import date

from dateutil.relativedelta import relativedelta
from lxml.html import etree

from weboob.browser.filters.html import Link, Attr
from weboob.browser.filters.standard import CleanText, CleanDecimal, RawText, Regexp, Date
from weboob.capabilities import NotAvailable
from weboob.capabilities.bank import Account, Investment, Loan
from weboob.browser.pages import HTMLPage, LoggedPage, FormNotFound
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.json import json
from weboob.exceptions import ActionNeeded, BrowserUnavailable
from weboob.tools.capabilities.bank.investments import is_isin_valid


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
            inv.id = re.search('cdReferentiel=(.*)', link.attrib['href']).group(1)
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

            if is_isin_valid(inv.code):
                inv.code_type = Investment.CODE_TYPE_ISIN

            yield inv
        if not account.type == account.TYPE_MARKET:
            inv = Investment()
            inv.code = "XX-liquidity"
            inv.label = "Liquidités"
            inv.valuation = CleanDecimal(None, True).filter(self.doc.xpath('//*[@id="valorisation_compte"]/table/tr[3]/td[2]'))
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

    def get_operations(self):
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
            inv.id = re.search('cdReferentiel=(.*)', cols[self.COL_LABEL].find('a').attrib['href']).group(1)
            inv.code = re.match('^[A-Z]+[0-9]+(.*)$', inv.id).group(1)
            inv.label = CleanText(None).filter(cols[self.COL_LABEL])
            inv.quantity = self.parse_decimal(cols[self.COL_QUANTITY])
            inv.unitprice = self.parse_decimal(cols[self.COL_UNITPRICE])
            inv.unitvalue = self.parse_decimal(cols[self.COL_UNITVALUE])
            inv.vdate = Date(CleanText(cols[self.COL_DATE], default=NotAvailable), default=NotAvailable)(self.doc)
            inv.valuation = self.parse_decimal(cols[self.COL_VALUATION])
            inv.diff = self.parse_decimal(cols[self.COL_PERF])
            diff_percent =  self.parse_decimal(cols[self.COL_PERF_PERCENT])
            inv.diff_percent = diff_percent / 100 if diff_percent else NotAvailable
            if is_isin_valid(inv.code):
                inv.code_type = Investment.CODE_TYPE_ISIN

            yield inv

    def parse_decimal(self, string):
        string = CleanText(None).filter(string)
        if string == '-' or string == '*':
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

    def get_operations(self):
        # skip on investments details
        if self.doc.xpath('//table/thead/tr/th[contains(text(), "ISIN")]'):
            return

        for tr in self.doc.xpath('//table[@id="tableau_histo_opes"]/tbody/tr | //form[@name="DetailOperationForm"]//table/tbody/tr[not(@id)][td[3]]'):
            tds = tr.findall('td')
            if len(CleanText(None).filter(tds[-1])) == 0:
                continue
            t = Transaction()
            t.type = Transaction.TYPE_BANK
            t.parse(date=CleanText(None).filter(tds[1]),
                    raw=CleanText(None).filter(tds[2]))
            t.amount = CleanDecimal(None, replace_dots=True, default=0).filter(tds[-1])
            # we check if transactions as sub transactions
            details_link = Regexp(Attr('./a', 'onclick', default=''), r"afficherDetailOperation\('([^']+)", default='')(tds[0])
            if details_link:
                has_trs = False
                for tr in self.browser.location(details_link).page.get_operations():
                    has_trs = True
                    yield tr
                # skipping main transaction with sub transactions
                if has_trs:
                    continue
            yield t

    def get_balance(self, account_type):
        for div in self.doc.xpath('//div[@class="block synthese_vie"]/div/div/div'):
            if 'Valorisation' in CleanText('.')(div):
                return CleanText('./p[@class="synthese_data_line_right_text"]')(div)


class AccountHistoryPage(LoggedPage, HTMLPage):
    def build_doc(self, content):
        content = re.sub(br'\*<E\w+', b'*', content)
        return super(AccountHistoryPage, self).build_doc(content)

    def get_coming(self):
        for tr in self.doc.xpath('//table[@id="tableauConsultationHisto"]/tbody/tr'):
            if 'Encours' in CleanText('./td')(tr):
                return CleanDecimal('./td//strong', replace_dots=True, sign=lambda x: -1, default=NotAvailable)(tr)

    def get_balance(self):
        for tr in self.doc.xpath('//table[@id="tableauConsultationHisto"]/tbody/tr'):
            if 'Solde' in CleanText('./td')(tr):
                return CleanText('./td/strong')(tr)

    def get_investments(self, account):
        return iter([])

    def select_period(self):
        # form = self.get_form(name='ConsultationHistoriqueOperationsForm')
        try:
            form = self.get_form(xpath='//form[@name="ConsultationHistoriqueOperationsForm" '
                                       ' or @name="form_historique_titres" '
                                       ' or @name="OperationsForm"]')
        except FormNotFound:
            return False

        form['dateRechercheDebut'] = (date.today() - relativedelta(years=2)).strftime('%d/%m/%Y')
        form['nbrEltsParPage'] = '100'
        form.submit()

        return True

    def get_operations(self):
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

    def get_operations(self):
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
            tr.type = tr.TYPE_DEFERRED_CARD
            if credit:
                tr.amount = CleanDecimal(None, replace_dots=True).filter(credit)
            elif debit:
                tr.amount = -abs(CleanDecimal(None, replace_dots=True).filter(debit))
            yield tr

    def is_loading(self):
        return bool(self.doc.xpath('//span[@class="loading"]'))


class WarningPage(LoggedPage, HTMLPage):
    def on_load(self):
        # if we can skip the CGU, then skip it
        if self.doc.xpath(u'//input[@class="bouton_valid01" and contains(@title, "Me le demander ultérieurement")]'):
            # Look for the request in the event listener registered to the button, can be harcoded, no variable part.
            # It is a POST request without data.
            url = self.browser.absurl('ReloadContext?action=1&', base=True)
            self.browser.location(url, method='POST')
        else:
            warning = self.doc.xpath(u'//div[@id="message_renouvellement_mot_passe"] | \
                                   //span[contains(text(), "Votre identifiant change")] | \
                                   //span[contains(text(), "Nouveau mot de passe")] | \
                                   //span[contains(text(), "Renouvellement de votre mot de passe")] |\
                                   //span[contains(text(), "Mieux vous connaître")]')
            if warning:
                raise ActionNeeded(warning[0].text)


class AccountsList(WarningPage):
    def get_iframe_url(self):
        iframe = self.doc.xpath('//iframe[@id="iframe_centrale"]')
        if iframe:
            return iframe[0].attrib['src']

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

                r = self.browser.open('/AsynchAjax', params=params)
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
                     'mes-comptes/compte-especes':                     Account.TYPE_CHECKING,
                     'mes-comptes/compte-courant/carte-bancaire':      Account.TYPE_CARD,
                     'mes-comptes/assurance-vie':                      Account.TYPE_LIFE_INSURANCE,
                     'mes-comptes/livret':                             Account.TYPE_SAVINGS,
                     'mes-comptes/pea':                                Account.TYPE_PEA,
                     'mes-comptes/ppe':                                Account.TYPE_PEA,
                     'mes-comptes/compte-titres-pea':                  Account.TYPE_MARKET,
                    }

    def get_list(self):
        accounts = []

        for cpt in self.doc.xpath('//div[contains(@class, " compte") and not(contains(@class, "compte_selected"))]'):

            # ignore auto assurance accounts
            if 'aut' in cpt.get('class'):
                continue

            account = Account()
            account._history_link = Link('./ul/li/a[contains(@id, "consulter_solde") '
                                         'or contains(@id, "historique") '
                                         'or contains(@id, "contrat") '
                                         'or contains(@id, "assurance_vie_operations")]')(cpt)

            # this is to test if access to the accounts info is blocked for different reasons
            page = self.browser.open(account._history_link).page
            if isinstance(page, LoanPage):
                account = Loan()

            account._history_link = Link('./ul/li/a[contains(@id, "consulter_solde") '
                                         'or contains(@id, "historique") '
                                         'or contains(@id, "contrat") '
                                         'or contains(@id, "assurance_vie_operations")]')(cpt)
            if isinstance(page, LoanPage):
                account.id = CleanText('(//p[@id="c_montantEmprunte"]//span[@class="valStatic"]//strong)[1]')(cpt)
                account.label = CleanText('(//p[@id="c_montantEmprunte"]//span[@class="valStatic"]//strong)[1]')(cpt)
                account.type = Account.TYPE_LOAN
                account_history_page = page
                account.total_amount = account_history_page.get_total_amount()
                account.next_payment_amount = account_history_page.get_next_payment_amount()
                account.next_payment_date = account_history_page.get_next_payment_date()
                account.account_label = account_history_page.get_account_label()
                account.subscription_date = account_history_page.get_subscription_date()
                account.maturity_date = account_history_page.get_maturity_date()

            if len(accounts) == 0:
                global_error_message = page.doc.xpath('//div[@id="as_renouvellementMIFID.do_"]/div[contains(text(), "Bonjour")] '
                                                      '| //div[@id="as_afficherMessageBloquantMigration.do_"]//div[@class="content_message"] '
                                                      '| //p[contains(text(), "Et si vous faisiez de Fortuneo votre banque principale")] '
                                                      '| //div[@id="as_renouvellementMotDePasse.do_"]//p[contains(text(), "votre mot de passe")]'
                                                      '| //div[@id="as_afficherSecuriteForteOTPIdentification.do_"]//span[contains(text(), "Pour valider ")]')
                if global_error_message:
                    raise ActionNeeded(CleanText('.')(global_error_message[0]))
            local_error_message = page.doc.xpath('//div[@id="error"]/p[@class="erreur_texte1"]')
            if local_error_message:
                raise BrowserUnavailable(CleanText('.')(local_error_message[0]))

            number = RawText('./a[contains(@class, "numero_compte")]')(cpt).replace(u'N° ', '')

            account.id = CleanText(None).filter(number).replace(u'N°', '')

            account._card_links = []
            card_link = Link('./ul/li/a[contains(text(), "Carte bancaire")]', default='')(cpt)
            if len(card_link) > 0:
                account._card_links.append(card_link)

            account.label = CleanText('./a[contains(@class, "numero_compte")]/@title')(cpt)

            for pattern, type in self.ACCOUNT_TYPES.items():
                if pattern in account._history_link:
                    account.type = type
                    break

            investment_page = None
            if account.type in {Account.TYPE_PEA, Account.TYPE_MARKET, Account.TYPE_LIFE_INSURANCE}:
                account._investment_link = Link('./ul/li/a[contains(@id, "portefeuille")]')(cpt)
                investment_page = self.browser.open(account._investment_link).page
                balance = investment_page.get_balance(account.type)
                if account.type in {Account.TYPE_PEA, Account.TYPE_MARKET}:
                    self.browser.investments[account.id] = list(self.browser.open(account._investment_link).page.get_investments(account))
            else:
                balance = page.get_balance()
                if account.type is not Account.TYPE_LOAN:
                    account.coming = page.get_coming()

            if account.type in {Account.TYPE_PEA, Account.TYPE_MARKET}:
                account.currency = investment_page.get_currency()
            else:
                account.currency = account.get_currency(balance)
            account.balance = CleanDecimal(None, replace_dots=True).filter(balance)

            if account.type in (Account.TYPE_CHECKING, Account.TYPE_SAVINGS):
                # Need a token sent by SMS to customers
                account.iban = NotAvailable

            if (account.label, account.id, account.balance) not in [(a.label, a.id, a.balance) for a in accounts]:
                accounts.append(account)
        return accounts


class GlobalAccountsList(LoggedPage, HTMLPage):
    def on_load(self):
        # Once the action needed is skipped, we can go to the accounts page
        self.browser.accounts_page.go()


class LoanPage(LoggedPage, HTMLPage):
    def get_balance(self):
        return CleanText(u'//p[@id="c_montantRestant"]//strong')(self.doc)

    def get_total_amount(self):
        return CleanDecimal(u'(//p[@id="c_montantEmprunte"]//strong)[2]', replace_dots=True)(self.doc)

    def get_next_payment_amount(self):
        return CleanDecimal(Regexp(CleanText(u'//p[@id="c_prochaineEcheance"]//strong'), u'(.*) le'), replace_dots=True)(self.doc)

    def get_next_payment_date(self):
        return Date(CleanText(u'//p[@id="c_prochaineEcheance"]//strong/strong'), dayfirst=True)(self.doc)

    def get_account_label(self):
        return CleanText(u'//p[@id="c_comptePrelevementl"]//strong')(self.doc)

    def get_subscription_date(self):
        return Date(CleanText(u'//p[@id="c_dateDebut"]//strong'), dayfirst=True)(self.doc)

    def get_maturity_date(self):
        return Date(CleanText(u'//p[@id="c_dateFin"]//strong'), dayfirst=True)(self.doc)
