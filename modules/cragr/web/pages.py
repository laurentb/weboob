# -*- coding: utf-8 -*-

# Copyright(C) 2013-2015  Romain Bignon
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

import re
from decimal import Decimal

from weboob.tools.date import parse_french_date
from weboob.capabilities.bank import Account
from weboob.deprecated.browser import Page, BrokenPageError
from weboob.tools.capabilities.bank.transactions import FrenchTransaction as Transaction


class HomePage(Page):
    def get_post_url(self):
        for script in self.document.xpath('//script'):
            text = script.text
            if text is None:
                continue

            m = re.search(r'var chemin = "([^"]+)"', text, re.MULTILINE)
            if m:
                return m.group(1)

        return None


class LoginPage(Page):
    def login(self, password):
        imgmap = {}
        for td in self.document.xpath('//table[@id="pave-saisie-code"]/tr/td'):
            a = td.find('a')
            num = a.text.strip()
            if num.isdigit():
                imgmap[num] = int(a.attrib['tabindex']) - 1

        self.browser.select_form(name='formulaire')
        self.browser.set_all_readonly(False)
        self.browser['CCCRYC'] = ','.join(['%02d' % imgmap[c] for c in password])
        self.browser['CCCRYC2'] = '0' * len(password)
        self.browser.submit(nologin=True)

    def get_result_url(self):
        return self.parser.tocleanstring(self.document.getroot())


class UselessPage(Page):
    pass


class LoginErrorPage(Page):
    pass


class _AccountsPage(Page):
    COL_LABEL    = 0
    COL_ID       = 2
    COL_VALUE    = 4
    COL_CURRENCY = 5

    TYPES = {'CCHQ':   Account.TYPE_CHECKING,
             'LIV A':  Account.TYPE_SAVINGS,
             'LDD':    Account.TYPE_SAVINGS,
             'PEL':    Account.TYPE_MARKET,
             'TITR':   Account.TYPE_MARKET,
            }

    def get_list(self):
        iban = None
        for tr in self.document.xpath('//table[@class="ca-table"]/tr'):
            if not tr.attrib.get('class', '').startswith('colcelligne'):
                continue

            cols = tr.findall('td')
            if not cols:
                continue

            account = Account()
            account.id = self.parser.tocleanstring(cols[self.COL_ID])
            account.label = self.parser.tocleanstring(cols[self.COL_LABEL])
            account.type = self.TYPES.get(account.label, Account.TYPE_UNKNOWN)
            balance = self.parser.tocleanstring(cols[self.COL_VALUE])
            # we have to ignore those accounts, because using NotAvailable
            # makes boobank and probably many others crash
            if balance in ('indisponible', ''):
                continue
            account.balance = Decimal(Transaction.clean_amount(balance))
            account.currency = account.get_currency(self.parser.tocleanstring(cols[self.COL_CURRENCY]))
            account._link = None

            a = cols[0].find('a')
            if a is not None:
                account._link = a.attrib['href'].replace(' ', '%20')
                page = self.browser.get_page(self.browser.openurl(account._link))
                url = page.get_iban_url()
                if url:
                    page = self.browser.get_page(self.browser.openurl(url))
                    iban = account.iban = page.get_iban()
                elif iban:
                    # In case there is no available IBAN on this account (for
                    # example saving account), calculate it from the previous
                    # IBAN.
                    bankcode = iban[4:9]
                    counter = iban[9:14]
                    key = 97 - ((int(bankcode) * 89 + int(counter) * 15 + int(account.id) * 3) % 97)
                    account.iban = iban[:4] + bankcode + counter + account.id + str(key)

            yield account

    def cards_pages(self):
        # Use a set because it is possible to see several times the same link.
        links = set()
        for line in self.document.xpath('//table[@class="ca-table"]/tr[@class="ligne-connexe"]'):
            try:
                link = line.xpath('.//a/@href')[0]
            except IndexError:
                pass
            else:
                if not link.startswith('javascript:'):
                    links.add(link)
        return links


class CardsPage(Page):
    def get_list(self):
        TABLE_XPATH = '//table[caption[@class="caption tdb-cartes-caption" or @class="ca-table caption"]]'

        cards_tables = self.document.xpath(TABLE_XPATH)

        if cards_tables:
            self.logger.debug('There are several cards')
            xpaths = {
                '_id': './caption/span[@class="tdb-cartes-num"]',
                'label1': './caption/span[contains(@class, "tdb-cartes-carte")]',
                'label2': './caption/span[@class="tdb-cartes-prop"]',
                'balance': './/tr/td[@class="cel-num"]',
                'currency': '//table/caption//span/text()[starts-with(.,"Montants en ")]',
                'link': './/tr//a/@href[contains(., "fwkaction=Detail")]',
            }
        else:
            self.logger.debug('There is only one card')
            xpaths = {
                '_id': './/tr/td[@class="cel-texte"]',
                'label1': './/tr[@class="ligne-impaire ligne-bleu"]/th',
                'label2': './caption/span[@class="tdb-cartes-prop"]/b',
                'balance': './/tr[last()-1]/td[@class="cel-num"]',
                'currency': '//table/caption//span/text()[starts-with(.,"Montants en ")]',
            }
            TABLE_XPATH = '(//table[@class="ca-table"])[1]'
            cards_tables = self.document.xpath(TABLE_XPATH)

        for table in cards_tables:
            get = lambda name: self.parser.tocleanstring(table.xpath(xpaths[name])[0])

            account = Account()
            account.type = account.TYPE_CARD
            account.id = ''.join(get('_id').split()[1:])
            account.label = '%s - %s' % (get('label1'),
                                         re.sub('\s*-\s*$', '', get('label2')))
            try:
                account.balance = Decimal(Transaction.clean_amount(table.xpath(xpaths['balance'])[-1].text))
                account.currency = account.get_currency(self.document
                        .xpath(xpaths['currency'])[0].replace("Montants en ", ""))
            except IndexError:
                account.balance = Decimal('0.0')

            if 'link' in xpaths:
                try:
                    account._link = table.xpath(xpaths['link'])[-1]
                except IndexError:
                    account._link = None
                else:
                    account._link = re.sub('[\n\r\t]+', '', account._link)
            else:
                account._link = self.url

            yield account

    def get_history(self, date_guesser):
        seen = set()
        lines = self.document.xpath('(//table[@class="ca-table"])[2]/tr')
        debit_date = None
        for i, line in enumerate(lines):
            is_balance = line.xpath('./td/@class="cel-texte cel-neg"')

            # It is possible to have three or four columns.
            cols = [self.parser.tocleanstring(td) for td in line.xpath('./td')]
            date = cols[0]
            label = cols[1]
            amount = cols[-1]

            t = Transaction(i)
            t.set_amount(amount)
            t.label = t.raw = label

            if is_balance:
                m = re.search('(\d+ [^ ]+ \d+)', label)
                if not m:
                    raise BrokenPageError('Unable to read card balance in history: %r' % label)

                debit_date = parse_french_date(m.group(1))

                # Skip the first line because it is balance
                if i == 0:
                    continue

                t.date = t.rdate = debit_date

                # Consider the second one as a positive amount to reset balance to 0.
                t.amount = -t.amount
            else:
                day, month = map(int, date.split('/', 1))
                t.rdate = date_guesser.guess_date(day, month)
                t.date = debit_date

            t.type = t.TYPE_CARD
            try:
                t.id = t.unique_id(seen)
            except UnicodeEncodeError:
                self.logger.debug(t)
                self.logger.debug(t.label)
                raise

            yield t


class AccountsPage(_AccountsPage):
    pass


class SavingsPage(_AccountsPage):
    COL_ID       = 1


class TransactionsPage(Page):
    def get_iban_url(self):
        for link in self.document.xpath('//a[contains(text(), "IBAN")]'):
            m = re.search("\('([^']+)'", link.get('href', ''))
            if m:
                return m.group(1)

        return None

    def get_iban(self):
        s = ''
        for font in self.document.xpath('(//td[font/b/text()="IBAN"])[1]/table//font'):
            s += self.parser.tocleanstring(font)
        return s

    def get_next_url(self):
        links = self.document.xpath('//span[@class="pager"]/a[@class="liennavigationcorpspage"]')
        if len(links) < 1:
            return None

        img = links[-1].find('img')
        if img.attrib.get('alt', '') == 'Page suivante':
            return links[-1].attrib['href']

        return None

    def get_order_by_date_url(self):
        try:
            link = self.document.xpath('//table[@class="ca-table"]/thead//a[text()="Date"]')[0].attrib['href']
        except IndexError:
            link = self.url
        return link

    COL_DATE  = 0
    COL_TEXT  = 1
    COL_DEBIT = None
    COL_CREDIT = -1

    TYPES = {'Paiement Par Carte':          Transaction.TYPE_CARD,
             'Retrait Au Distributeur':     Transaction.TYPE_WITHDRAWAL,
             'Frais':                       Transaction.TYPE_BANK,
             'Cotisation':                  Transaction.TYPE_BANK,
             'Virement Emis':               Transaction.TYPE_TRANSFER,
             'Virement':                    Transaction.TYPE_TRANSFER,
             'Cheque Emis':                 Transaction.TYPE_CHECK,
             'Remise De Cheque':            Transaction.TYPE_DEPOSIT,
             'Prelevement':                 Transaction.TYPE_ORDER,
             'Prelevt':                     Transaction.TYPE_ORDER,
             'Prelevmnt':                   Transaction.TYPE_ORDER,
            }

    def get_history(self, date_guesser):
        i = 0
        for tr in self.document.xpath('//table[@class="ca-table"]//tr'):
            parent = tr.getparent()
            while parent is not None and parent.tag != 'table':
                parent = parent.getparent()

            if parent.attrib.get('class', '') != 'ca-table':
                continue

            if tr.attrib.get('class', '') == 'tr-thead':
                heads = tr.findall('th')
                for i, head in enumerate(heads):
                    key = self.parser.tocleanstring(head)
                    if key == u'Débit':
                        self.COL_DEBIT = i - len(heads)
                    if key == u'Crédit':
                        self.COL_CREDIT = i - len(heads)
                    if key == u'Libellé':
                        self.COL_TEXT = i

            if not tr.attrib.get('class', '').startswith('ligne-'):
                continue

            cols = tr.findall('td')

            # On loan accounts, there is a ca-table with a summary. Skip it.
            if tr.find('th') is not None or len(cols) < 3:
                continue

            t = Transaction(i)

            col_text = cols[self.COL_TEXT]
            if len(col_text.xpath('.//br')) == 0:
                col_text = cols[self.COL_TEXT+1]

            raw = self.parser.tocleanstring(col_text)
            date = self.parser.tocleanstring(cols[self.COL_DATE])
            credit = self.parser.tocleanstring(cols[self.COL_CREDIT])
            if self.COL_DEBIT is not None:
                debit =  self.parser.tocleanstring(cols[self.COL_DEBIT])
            else:
                debit = ''

            day, month = map(int, date.split('/', 1))
            t.date = date_guesser.guess_date(day, month)
            t.rdate = t.date
            t.raw = raw

            # On some accounts' history page, there is a <font> tag in columns.
            if col_text.find('font') is not None:
                col_text = col_text.find('font')

            t.category = unicode(col_text.text.strip())
            t.label = re.sub('(.*)  (.*)', r'\2', t.category).strip()

            sub_label = col_text.find('br').tail
            if sub_label is not None and (len(t.label) < 3 or t.label == t.category or len(re.findall('[^\w\s]', sub_label))/float(len(sub_label)) < len(re.findall('\d', t.label))/float(len(t.label))):
                t.label = unicode(sub_label.strip())
            # Sometimes, the category contains the label, even if there is another line with it again.
            t.category = re.sub('(.*)  .*', r'\1', t.category).strip()

            t.type = self.TYPES.get(t.category, t.TYPE_UNKNOWN)

            # Parse operation date in label (for card transactions for example)
            m = re.match('(?P<text>.*) (?P<dd>[0-3]\d)/(?P<mm>[0-1]\d)$', t.label)
            if not m:
                m = re.match('^(?P<dd>[0-3]\d)/(?P<mm>[0-1]\d) (?P<text>.*)$', t.label)
            if m:
                if t.type in (t.TYPE_CARD, t.TYPE_WITHDRAWAL):
                    t.rdate = date_guesser.guess_date(int(m.groupdict()['dd']), int(m.groupdict()['mm']), change_current_date=False)
                t.label = m.groupdict()['text'].strip()

            # Strip city or other useless information from label.
            t.label = re.sub('(.*)  .*', r'\1', t.label).strip()
            t.set_amount(credit, debit)
            yield t

            i += 1
