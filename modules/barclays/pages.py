# -*- coding: utf-8 -*-

# Copyright(C) 2012 Romain Bignon
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
from decimal import Decimal, InvalidOperation
import re

from weboob.deprecated.browser import Page
from weboob.capabilities.bank import Account, Investment, NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


class LoginPage(Page):
    def login(self, login, passwd):
        self.browser.select_form(name='frmLogin')
        self.browser['username'] = login.encode(self.browser.ENCODING)
        self.browser['password'] = passwd.encode(self.browser.ENCODING)
        self.browser.submit(nologin=True)

    def has_redirect(self):
        if len(self.document.getroot().xpath('//form')) > 0:
            return False
        else:
            return True


class Login2Page(Page):
    def login(self, secret):
        label = self.document.xpath('//span[@class="PF_LABEL"]')[0].text.strip()
        letters = ''
        for n in re.findall('(\d+)', label):
            letters += secret[int(n) - 1]

        self.browser.select_form(name='frmControl')
        self.browser['word'] = letters.encode(self.browser.ENCODING)
        self.browser.submit(name='valider', nologin=True)


class IndexPage(Page):
    pass


class AccountsPage(Page):
    ACCOUNT_TYPES = {u'Epargne':                Account.TYPE_SAVINGS,
                     u'Liquidités':             Account.TYPE_CHECKING,
                     u'Titres':                 Account.TYPE_MARKET,
                     u'Prêts':                  Account.TYPE_LOAN,
                    }

    def get_list(self):
        accounts = []

        for block in self.document.xpath('//div[@class="pave"]/div'):
            head_type = block.xpath('./div/span[@class="accGroupLabel"]')[0].text.strip()
            account_type = self.ACCOUNT_TYPES.get(head_type, Account.TYPE_UNKNOWN)
            for tr in block.cssselect('ul li.tbord_account'):
                id = tr.attrib.get('id', '')
                if id.find('contratId') != 0:
                    self.logger.warning('Unable to parse contract ID: %r' % id)
                    continue
                id = id[id.find('contratId')+len('contratId'):]

                link = tr.cssselect('span.accountLabel a')[0]
                balance = Decimal(FrenchTransaction.clean_amount(tr.cssselect('span.accountTotal')[0].text))

                account = Account()
                account._attached_acc = None
                account.id = id
                account.label = unicode(link.text.strip())
                account.type = account_type
                account.balance = balance
                account.currency = account.get_currency(tr.cssselect('span.accountDev')[0].text)
                account._link = link.attrib['href']
                if id.endswith('CRT'):
                    self.populate_cards(account)

                accounts.append(account)

        if len(accounts) == 0:
            # Sometimes, accounts are only in javascript...
            for script in self.document.xpath('//script'):
                text = script.text
                if text is None:
                    continue
                if 'remotePerso' not in text:
                    continue

                account = None
                attribs = {}
                account_type = Account.TYPE_UNKNOWN
                for line in text.split('\n'):
                    line = line.strip()
                    m = re.match("data.libelle = '(.*)';", line)
                    if m:
                        account_type = self.ACCOUNT_TYPES.get(m.group(1), Account.TYPE_UNKNOWN)
                    elif line == 'var remotePerso = new Object;':
                        account = Account()
                    elif account is not None:
                        m = re.match("remotePerso.(\w+) = '?(.*?)'?;", line)
                        if m:
                            attribs[m.group(1)] = m.group(2)
                        elif line.startswith('listProduitsGroup'):
                            account.id = attribs['refContrat']

                            account.label = attribs['libelle']
                            account.type = account_type
                            account.balance = Decimal(FrenchTransaction.clean_amount(attribs['soldeDateOpeValeurFormatted']))
                            account.currency = account.get_currency(attribs['codeDevise'])
                            account._link = 'tbord.do?id=%s&%s' % (attribs['id'], self.browser.SESSION_PARAM)
                            account._attached_acc = None

                            if account.id.endswith('CRT'):
                                self.populate_cards(account)
                            elif any([word in account.label for word in ['COURANT', 'joint', 'perso']]):
                                account.type = account.TYPE_CHECKING
                            elif account.id.endswith('TTR'):
                                account.type = account.TYPE_MARKET
                            elif re.match('^\d+C$', account.id):
                                account.type = account.TYPE_LIFE_INSURANCE
                            elif re.match('^\d+PRT$', account.id):
                                account.type = account.TYPE_LOAN
                            elif not account.type:
                                account.type = account.TYPE_SAVINGS

                            accounts.append(account)
                            account = None

        return accounts

    def populate_cards(self, account):
        account.type = account.TYPE_CARD
        account.coming = account.balance
        account.balance = Decimal('0.0')
        doc = self.browser.get_document(self.browser.openurl(account._link))
        self.browser.openurl(self.url)
        account._attached_acc = ''.join(re.findall('\d', doc.xpath(u'//td[contains(text(), "Carte rattachée")]')[0].text))


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^RET DAB (?P<text>.*?) RETRAIT DU (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}).*'),
                                                              FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^RET DAB (?P<text>.*?) CARTE ?:.*'),
                                                              FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^RET DAB (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2}) (?P<text>.*?) CARTE .*'),
                                                              FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^(?P<text>.*) RETRAIT DU (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) .*'),
                                                              FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('(\w+) (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) CB[:\*][^ ]+ (?P<text>.*)'),
                                                              FrenchTransaction.TYPE_CARD),
                (re.compile('^(?P<category>VIR(EMEN)?T? (SEPA)?(RECU|FAVEUR)?)( /FRM)?(?P<text>.*)'),
                                                              FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^PRLV (?P<text>.*) (REF \w+)?$'),FrenchTransaction.TYPE_ORDER),
                (re.compile('^CHEQUE.*? (REF \w+)?$'),        FrenchTransaction.TYPE_CHECK),
                (re.compile('^(AGIOS /|FRAIS) (?P<text>.*)'), FrenchTransaction.TYPE_BANK),
                (re.compile('^(CONVENTION \d+ )?COTIS(ATION)? (?P<text>.*)'),
                                                              FrenchTransaction.TYPE_BANK),
                (re.compile('^REMISE (?P<text>.*)'),          FrenchTransaction.TYPE_DEPOSIT),
                (re.compile('^(?P<text>.*)( \d+)? QUITTANCE .*'),
                                                              FrenchTransaction.TYPE_ORDER),
                (re.compile('^.* LE (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2})$'),
                                                              FrenchTransaction.TYPE_UNKNOWN),
               ]


class HistoryBasePage(Page):
    def iter_investments(self):
        self.logger.warning('Do not support investments on account of type %s' % type(self).__name__)
        return iter([])

    def get_history(self):
        self.logger.warning('Do not support history on account of type %s' % type(self).__name__)
        return iter([])

    def get_next_page(self):
        link = self.document.xpath('//a[span[contains(text(), "Suiv.")]]')
        if link:
            return link[0].attrib['href']


class TransactionsPage(HistoryBasePage):
    def get_history(self):
        for tr in self.document.xpath('//table[@id="operation"]/tbody/tr'):
            tds = tr.findall('td')

            if len(tds) < 5:
                continue

            t = Transaction()

            date = u''.join([txt.strip() for txt in tds[0].itertext()])
            raw = u' '.join([txt.strip() for txt in tds[1].itertext()])
            debit = u''.join([txt.strip() for txt in tds[-3].itertext()])
            credit = u''.join([txt.strip() for txt in tds[-2].itertext()])
            t.parse(date, re.sub(r'[ ]+', ' ', raw))
            t.set_amount(credit, debit)
            t._coming = False

            if t.raw.startswith('ACHAT CARTE -DEBIT DIFFERE') or 'ACHAT-DEBIT DIFFERE' in t.raw:
                t.type = t.TYPE_CARD_SUMMARY

            yield t


class CardPage(HistoryBasePage):
    def get_history(self):
        debit_date = None
        coming = True
        for tr in self.document.xpath('//table[@class="report"]/tbody/tr'):
            tds = tr.findall('td')

            if len(tds) == 2:
                # headers
                m = re.match('.* (\d+)/(\d+)/(\d+)', tds[0].text.strip())
                debit_date = datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                if debit_date < datetime.date.today():
                    coming = False

            if len(tds) != 3:
                continue

            t = Transaction()
            date = u''.join([txt.strip() for txt in tds[0].itertext()])
            raw = u' '.join([txt.strip() for txt in tds[1].itertext()])
            amount = u''.join([txt.strip() for txt in tds[-1].itertext()])
            t.parse(date, re.sub(r'[ ]+', ' ', raw))
            if debit_date is not None:
                t.date = debit_date
            t.label = unicode(tds[1].find('span').text.strip())
            t.type = t.TYPE_DEFERRED_CARD
            t._coming = coming
            t.set_amount(amount)
            yield t


class ValuationPage(HistoryBasePage):
    pass


class LoanPage(HistoryBasePage):
    pass


class MarketPage(HistoryBasePage):
    pass


class AssurancePage(HistoryBasePage):
    def iter_investments(self):
        for tr in self.document.xpath('//table[@id="support"]/tbody/tr'):
            tds = tr.findall('td')

            inv = Investment()
            inv.label = self.parser.tocleanstring(tds[0])
            inv.code = NotAvailable

            try:
                inv.quantity = Decimal(Transaction.clean_amount(self.parser.tocleanstring(tds[1])))
            except InvalidOperation:
                pass

            try:
                inv.unitvalue = Decimal(Transaction.clean_amount(self.parser.tocleanstring(tds[2])))
            except InvalidOperation:
                pass

            inv.valuation = Decimal(Transaction.clean_amount(self.parser.tocleanstring(tds[3])))
            inv.set_empty_fields(NotAvailable)
            yield inv


class LogoutPage(Page):
    pass
