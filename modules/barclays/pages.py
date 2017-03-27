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


import datetime, re
from decimal import Decimal

from weboob.browser.pages import HTMLPage, LoggedPage, PDFPage
from weboob.browser.filters.standard import CleanText, CleanDecimal
from weboob.browser.filters.html import Attr, Link
from weboob.capabilities.bank import Account, Investment, NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)


class LoginPage(HTMLPage):
    def login(self, login, passwd):
        form = self.get_form(name='frmLogin')
        form['username'] = login
        form['password'] = passwd
        form.submit()

    def has_redirect(self):
        return not len(self.doc.getroot().xpath('//form')) > 0


class Login2Page(HTMLPage):
    def login(self, secret):
        label = self.doc.xpath('//span[@class="PF_LABEL"]')[0].text.strip()
        letters = ''
        for n in re.findall('(\d+)', label):
            letters += secret[int(n) - 1]

        form = self.get_form(name='frmControl', submit='//*[@name="valider"]')
        form['word'] = letters
        form.submit()


class IndexPage(HTMLPage):
    pass


class AccountsPage(LoggedPage, HTMLPage):
    ACCOUNT_TYPES = {u'Epargne':                Account.TYPE_SAVINGS,
                     u'Liquidités':             Account.TYPE_CHECKING,
                     u'Titres':                 Account.TYPE_MARKET,
                     u'Prêts':                  Account.TYPE_LOAN,
                    }

    def get_list(self):
        accounts = []

        for block in self.doc.xpath('//div[@class="pave"]/div'):
            head_type = block.xpath('./div/span[@class="accGroupLabel"]')[0].text.strip()
            account_type = self.ACCOUNT_TYPES.get(head_type, Account.TYPE_UNKNOWN)
            for tr in block.cssselect('ul li.tbord_account'):
                id = tr.attrib.get('id', '')
                if id.find('contratId') != 0:
                    self.logger.warning('Unable to parse contract ID: %r' % id)
                    continue
                id = id[id.find('contratId')+len('contratId'):]

                link = tr.cssselect('span.accountLabel a')[0]

                balance = CleanDecimal('.//span[@class="accountTotal"]', replace_dots=True)(tr)

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
            for script in self.doc.xpath('//script'):
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
                            elif any([word in account.label.lower() for word in ['courant', 'joint', 'perso']]):
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

    def get_ibanlink(self):
        return Link('//a[@id="editionRibLevel2link"]', default=None)(self.doc)

    def populate_cards(self, account):
        account.type = account.TYPE_CARD
        account.coming = account.balance
        account.balance = Decimal('0.0')
        doc = self.browser.open(account._link).page.doc
        self.browser.open(self.browser.url)
        account._attached_acc = ''.join(re.findall('\d', doc.xpath(u'//td[contains(text(), "Carte rattachée")]')[0].text))


class IbanPage(LoggedPage, HTMLPage):
    def get_list(self):
        form = self.get_form(name='frmRIB')
        trs = self.doc.xpath('//tr[td[a[@checkaccount]]]')
        return {'form': form, 'list': \
            {CleanText('./td[1]', replace=[(' ', '')])(tr): Attr('.//a[@checkaccount]', 'checkaccount')(tr) for tr in trs}}


class IbanPDFPage(LoggedPage, PDFPage):
    def get_iban(self):
        ibans = re.findall(r'1001\d{3}.9\d{3}.73Tm\/F18Tf000rg\(([A-Z\d]+)\)', "".join(self.doc.split()))
        return NotAvailable if not len(ibans) else CleanText().filter(ibans[0])


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


class HistoryBasePage(HTMLPage):
    def iter_investments(self):
        self.logger.warning('Do not support investments on account of type %s' % type(self).__name__)
        return iter([])

    def get_history(self):
        self.logger.warning('Do not support history on account of type %s' % type(self).__name__)
        return iter([])

    def get_next_page(self):
        link = self.doc.xpath('//a[span[contains(text(), "Suiv.")]]')
        if link:
            return link[0].attrib['href']


class TransactionsPage(LoggedPage, HistoryBasePage):
    def get_history(self):
        for tr in self.doc.xpath('//table[@id="operation"]/tbody/tr'):
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


class CardPage(LoggedPage, HistoryBasePage):
    def get_history(self):
        debit_date = None
        coming = True
        for tr in self.doc.xpath('//table[@class="report"]/tbody/tr'):
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


class ValuationPage(LoggedPage, HistoryBasePage):
    pass


class LoanPage(LoggedPage, HistoryBasePage):
    pass


class MarketPage(LoggedPage, HistoryBasePage):
    pass


class AssurancePage(LoggedPage, HistoryBasePage):
    def iter_investments(self):
        for tr in self.doc.xpath('//table[@id="support"]/tbody/tr'):
            tds = tr.findall('td')

            inv = Investment()
            inv.label = CleanText('.')(tds[0])
            inv.code = NotAvailable

            inv.quantity = MyDecimal('.')(tds[1])
            inv.unitvalue = MyDecimal('.')(tds[2])
            inv.valuation = MyDecimal('.')(tds[3])
            yield inv


class LogoutPage(HTMLPage):
    pass
