# -*- coding: utf-8 -*-

# Copyright(C) 2012 Gilles-Alexandre Quenot
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import re
import sys
from time import sleep
from datetime import date

from dateutil.relativedelta import relativedelta
from lxml.html import etree

from weboob.browser.elements import method, ItemElement
from weboob.browser.filters.html import Link, Attr
from weboob.browser.filters.standard import CleanText, CleanDecimal, RawText, Regexp, Date
from weboob.capabilities import NotAvailable
from weboob.capabilities.bank import Account, Investment, Loan, AccountOwnership
from weboob.capabilities.profile import Person
from weboob.browser.pages import HTMLPage, LoggedPage, FormNotFound, CsvPage
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.capabilities.bank.investments import create_french_liquidity
from weboob.tools.json import json
from weboob.tools.date import parse_french_date
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
        if account.type != account.TYPE_MARKET:
            valuation = CleanDecimal(None, True).filter(self.doc.xpath('//*[@id="valorisation_compte"]/table/tr[3]/td[2]'))
            yield create_french_liquidity(valuation)

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

            inv.label = CleanText(None).filter(cols[self.COL_LABEL])
            inv.quantity = self.parse_decimal(cols[self.COL_QUANTITY], True)
            inv.unitprice = self.parse_decimal(cols[self.COL_UNITPRICE], False)
            inv.unitvalue = self.parse_decimal(cols[self.COL_UNITVALUE], False)
            inv.vdate = Date(CleanText(cols[self.COL_DATE], default=NotAvailable), dayfirst=True, default=NotAvailable)(self.doc)
            inv.valuation = self.parse_decimal(cols[self.COL_VALUATION], False)
            inv.diff = self.parse_decimal(cols[self.COL_PERF], True)
            diff_percent = self.parse_decimal(cols[self.COL_PERF_PERCENT], True)
            inv.diff_ratio = diff_percent / 100 if diff_percent else NotAvailable
            code = re.match('^[A-Z]+[0-9]+(.*)$', inv.id).group(1)
            if is_isin_valid(code):
                inv.code = CleanText().filter(code)
                inv.code_type = Investment.CODE_TYPE_ISIN
            else:
                inv.code = inv.code_type = NotAvailable
            yield inv

    def parse_decimal(self, string, replace_dots):
        string = CleanText(None).filter(string)
        if string in ('-', '*'):
            return NotAvailable
        # Decimal separators can be ',' or '.' depending on the column
        if replace_dots:
            return CleanDecimal.French().filter(string)
        return CleanDecimal.SI().filter(string)

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
            label           = re.sub(r'\s+', ' ', label).strip()
            amount          = tables[i].xpath("./td[5]/text() | ./td[6]/text()")

            operation.parse(date=date_oper, raw=label, vdate=date_val)

            # There is no difference between card transaction and deferred card transaction
            # on the history.
            if operation.type == FrenchTransaction.TYPE_CARD:
                operation.bdate = operation.rdate

            # Needed because operation.parse overwrite operation.label
            # Theses lines must run after operation.parse.
            if tables[i].xpath("./td[4]/div/text()"):
                label = tables[i].xpath("./td[4]/div/text()")[0]
            else:
                label = tables[i].xpath("./td[4]/text()")[0]
            operation.label = re.sub(r'\s+', ' ', label).strip()

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
            tr.rdate = tr.bdate = tr.parse_date(rdate)
            tr.type = tr.TYPE_DEFERRED_CARD
            if credit:
                tr.amount = CleanDecimal(None, replace_dots=True).filter(credit)
            elif debit:
                tr.amount = -abs(CleanDecimal(None, replace_dots=True).filter(debit))
            yield tr

    def is_loading(self):
        return bool(self.doc.xpath('//span[@class="loading"]'))


class AccountsList(LoggedPage, HTMLPage):
    def has_action_needed(self):
        # NB: The CGUs happens on every page as long as it is not skipped or
        # validated. The implementation is done in the Accounts page because
        # we decide to skip the CGUs in browser.iter_accounts()
        skip_button = self.doc.xpath(u'//input[@class="bouton_valid01" and contains(@title, "Me le demander ultérieurement")]')
        if skip_button:
            return True
        else:
            warning = self.doc.xpath(u'//div[@id="message_renouvellement_mot_passe"] | \
                                   //span[contains(text(), "Votre identifiant change")] | \
                                   //span[contains(text(), "Nouveau mot de passe")] | \
                                   //span[contains(text(), "Renouvellement de votre mot de passe")] |\
                                   //span[contains(text(), "Mieux vous connaître")] |\
                                   //span[contains(text(), "Souscrivez au Livret + en quelques clics")] |\
                                   //p[@class="warning" and contains(text(), "Cette opération sensible doit être validée par un code sécurité envoyé par SMS ou serveur vocal")]'
                                   )
            if warning:
                raise ActionNeeded(warning[0].text)

    @method
    class fill_person_name(ItemElement):
        klass = Account

        # Contains the title (M., Mme., etc) + last name.
        # The first name isn't available in the person's details.
        obj_name = CleanText('//span[has-class("mon_espace_nom")]')

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
                account.ownership = account_history_page.get_owner()

            if len(accounts) == 0:
                global_error_message = page.doc.xpath('//div[@id="as_renouvellementMIFID.do_"]/div[contains(text(), "Bonjour")] '
                                                      '| //div[@id="as_afficherMessageBloquantMigration.do_"]//div[@class="content_message"] '
                                                      '| //p[contains(text(), "Et si vous faisiez de Fortuneo votre banque principale")] '
                                                      '| //div[@id="as_renouvellementMotDePasse.do_"]//p[contains(text(), "votre mot de passe")]'
                                                      '| //div[@id="as_afficherSecuriteForteOTPIdentification.do_"]//span[contains(text(), "Pour valider ")]')
                if global_error_message:
                    if "Et si vous faisiez de Fortuneo votre banque principale" in CleanText(global_error_message)(self):
                        self.browser.location('/ReloadContext', data={'action': 4})
                        return
                    raise ActionNeeded(CleanText('.')(global_error_message[0]))
            local_error_message = page.doc.xpath('//div[@id="error"]/p[@class="erreur_texte1"]')
            if local_error_message:
                raise BrowserUnavailable(CleanText('.')(local_error_message[0]))

            account.id = account.number = CleanText('./a[contains(@class, "numero_compte")]/div')(cpt).replace(u'N° ', '')
            account._ca = CleanText('./a[contains(@class, "numero_compte")]/@rel')(cpt)

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
            elif balance:
                account.currency = account.get_currency(balance)
            if account.type == Account.TYPE_LIFE_INSURANCE:
                # Life Insurance balance uses '.' instead of ','
                account.balance = CleanDecimal.SI().filter(balance)
            else:
                account.balance = CleanDecimal.French().filter(balance)

            if account.type in (Account.TYPE_CHECKING, Account.TYPE_SAVINGS):
                # Need a token sent by SMS to customers
                account.iban = NotAvailable

            if account.type is not Account.TYPE_LOAN:
                regexp = re.search(r'(m\. |mme\. )(.+)', CleanText('//span[has-class("mon_espace_nom")]')(self.doc), re.IGNORECASE)
                if regexp and len(regexp.groups()) == 2:
                    gender = regexp.group(1).replace('.', '').rstrip()
                    name = regexp.group(2)
                    label = account.label
                    if re.search(r'(m|mr|me|mme|mlle|mle|ml)\.? (.*)\bou (m|mr|me|mme|mlle|mle|ml)\b(.*)', label, re.IGNORECASE):
                        account.ownership = AccountOwnership.CO_OWNER
                    elif re.search(r'{} {}'.format(gender, name), label, re.IGNORECASE):
                        account.ownership = AccountOwnership.OWNER
                    else:
                        account.ownership = AccountOwnership.ATTORNEY

            if (account.label, account.id, account.balance) not in [(a.label, a.id, a.balance) for a in accounts]:
                accounts.append(account)
        return accounts


class FakeActionPage(LoggedPage, HTMLPage):
    pass

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

    def get_owner(self):
        if bool(CleanText('//p[@id="c_emprunteurSecondaire"]')(self.doc)):
            return AccountOwnership.CO_OWNER
        return AccountOwnership.OWNER


class ProfilePage(LoggedPage, HTMLPage):
    def get_csv_link(self):
        return Link('//div[@id="bloc_telecharger"]//a[@id="telecharger_donnees"]', default=NotAvailable)(self.doc)

    @method
    class get_profile(ItemElement):
        klass = Person

        obj_phone = Regexp(CleanText('//div[@id="consultationform_telephones"]/p[@id="c_numeroPortable"]'), '([\d\*]+)', default=None)
        obj_email = CleanText('//div[@id="modification_email"]//p[@id="c_email_actuel"]/span')
        obj_address = CleanText('//div[@id="consultationform_adresse_domicile"]/div[@class="container"]//span')
        obj_job = CleanText('//div[@id="consultationform_informations_complementaires"]/p[@id="c_profession"]/span')
        obj_job_activity_area = CleanText('//div[@id="consultationform_informations_complementaires"]/p[@id="c_secteurActivite"]/span')
        obj_company_name = CleanText('//div[@id="consultationform_informations_complementaires"]/p[@id="c_employeur"]/span')


class ProfilePageCSV(LoggedPage, CsvPage):
    ENCODING = 'latin_1'
    if sys.version_info.major > 2:
        FMTPARAMS = {'delimiter': ';'}
    else:
        FMTPARAMS = {'delimiter': b';'}

    def get_profile(self):
        d = {el[0]: el[1] for el in self.doc}
        profile = Person()
        profile.name = '%s %s' % (d['Nom'], d['Prénom'])
        profile.birth_date = parse_french_date(d['Date de naissance']).date()
        profile.address = '%s %s %s' % (d['Adresse de correspondance'], d['Code postal résidence fiscale'], d['Ville adresse de correspondance'])
        profile.country = d['Pays adresse de correspondance']
        profile.email = d['Adresse e-mail']
        profile.phone = d.get('Téléphone portable')
        profile.job_activity_area = d.get('Secteur d\'activité')
        profile.job = d.get('Situation professionnelle')
        profile.company_name = d.get('Employeur')
        profile.family_situation = d.get('Situation familiale')
        return profile


class SecurityPage(LoggedPage, HTMLPage):
    pass
