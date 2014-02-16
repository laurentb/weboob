# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Julien Veyssier
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
from urlparse import urlparse, parse_qs
from decimal import Decimal
import re
from dateutil.relativedelta import relativedelta

from weboob.tools.browser import BasePage, BrowserIncorrectPassword, BrokenPageError
from weboob.tools.ordereddict import OrderedDict
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.date import parse_french_date


class LoginPage(BasePage):
    def login(self, login, passwd):
        self.browser.select_form(name='ident')
        self.browser['_cm_user'] = login.encode(self.browser.ENCODING)
        self.browser['_cm_pwd'] = passwd.encode(self.browser.ENCODING)
        self.browser.submit(nologin=True)


class LoginErrorPage(BasePage):
    pass


class ChangePasswordPage(BasePage):
    def on_loaded(self):
        raise BrowserIncorrectPassword('Please change your password')

class VerifCodePage(BasePage):
    def on_loaded(self):
        raise BrowserIncorrectPassword('Unable to login: website asks a code from a card')

class InfoPage(BasePage):
    pass


class EmptyPage(BasePage):
    pass


class TransfertPage(BasePage):
    pass


class UserSpacePage(BasePage):
    pass


class AccountsPage(BasePage):
    TYPES = {'C/C':             Account.TYPE_CHECKING,
             'Livret':          Account.TYPE_SAVINGS,
             'Pret':            Account.TYPE_LOAN,
             'Compte Courant':  Account.TYPE_CHECKING,
             'Compte Cheque':   Account.TYPE_CHECKING,
             'Compte Epargne':  Account.TYPE_SAVINGS,
            }

    def get_list(self):
        accounts = OrderedDict()

        for tr in self.document.getiterator('tr'):
            first_td = tr.getchildren()[0]
            if (first_td.attrib.get('class', '') == 'i g' or first_td.attrib.get('class', '') == 'p g') \
               and first_td.find('a') is not None:

                a = first_td.find('a')
                link = a.get('href', '')
                if link.startswith('POR_SyntheseLst'):
                    continue

                url = urlparse(link)
                p = parse_qs(url.query)
                if not 'rib' in p:
                    continue

                for i in (2,1):
                    balance = FrenchTransaction.clean_amount(tr.getchildren()[i].text)
                    currency = Account.get_currency(tr.getchildren()[i].text)
                    if len(balance) > 0:
                        break
                balance = Decimal(balance)

                id = p['rib'][0]
                if id in accounts:
                    account = accounts[id]
                    if not account.coming:
                        account.coming = Decimal('0.0')
                    account.coming += balance
                    account._card_links.append(link)
                    continue

                account = Account()
                account.id = id
                account.label = unicode(a.text).strip().lstrip(' 0123456789').title()

                for pattern, actype in self.TYPES.iteritems():
                    if account.label.startswith(pattern):
                        account.type = actype

                account._link_id = link
                account._card_links = []

                # Find accounting amount
                page = self.browser.get_document(self.browser.openurl(link))
                coming = self.find_amount(page, u"Opérations à venir")
                accounting = self.find_amount(page, u"Solde comptable")

                if accounting is not None and accounting + (coming or Decimal('0')) != balance:
                    self.logger.warning('%s + %s != %s' % (accounting, coming, balance))

                if accounting is not None:
                    balance = accounting

                if coming is not None:
                    account.coming = coming
                account.balance = balance
                account.currency = currency

                accounts[account.id] = account

        return accounts.itervalues()

    def find_amount(self, page, title):
        try:
            td = page.xpath(u'//th[contains(text(), "%s")]/../td' % title)[0]
        except IndexError:
            return None
        else:
            return Decimal(FrenchTransaction.clean_amount(td.text))


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^VIR(EMENT)? (?P<text>.*)'), FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^PRLV (?P<text>.*)'),        FrenchTransaction.TYPE_ORDER),
                (re.compile('^(?P<text>.*) CARTE \d+ PAIEMENT CB\s+(?P<dd>\d{2})(?P<mm>\d{2}) ?(.*)$'),
                                                          FrenchTransaction.TYPE_CARD),
                (re.compile('^RETRAIT DAB (?P<dd>\d{2})(?P<mm>\d{2}) (?P<text>.*) CARTE [\*\d]+'),
                                                          FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^CHEQUE( (?P<text>.*))?$'),  FrenchTransaction.TYPE_CHECK),
                (re.compile('^(F )?COTIS\.? (?P<text>.*)'),FrenchTransaction.TYPE_BANK),
                (re.compile('^(REMISE|REM CHQ) (?P<text>.*)'),FrenchTransaction.TYPE_DEPOSIT),
               ]

    _is_coming = False


class OperationsPage(BasePage):
    def get_history(self):
        index = 0
        for tr in self.document.getiterator('tr'):
            # columns can be:
            # - date | value | operation | debit | credit | contre-valeur
            # - date | value | operation | debit | credit
            # - date | operation | debit | credit
            # That's why we skip any extra columns, and take operation, debit
            # and credit from last instead of first indexes.
            tds = tr.getchildren()[:5]
            if len(tds) < 4:
                continue

            if tds[0].attrib.get('class', '') == 'i g' or \
               tds[0].attrib.get('class', '') == 'p g' or \
               tds[0].attrib.get('class', '').endswith('_c1 c _c1'):
                operation = Transaction(index)
                index += 1

                parts = [txt.strip() for txt in tds[-3].itertext() if len(txt.strip()) > 0]

                # To simplify categorization of CB, reverse order of parts to separate
                # location and institution.
                if parts[0].startswith('PAIEMENT CB'):
                    parts.reverse()

                date = tds[0].text
                vdate = tds[1].text if len(tds) >= 5 else None
                raw = u' '.join(parts)

                operation.parse(date=date, vdate=vdate, raw=raw)

                credit = self.parser.tocleanstring(tds[-1])
                debit = self.parser.tocleanstring(tds[-2])
                operation.set_amount(credit, debit)
                yield operation

    def go_next(self):
        form = self.document.xpath('//form[@id="paginationForm"]')
        if len(form) == 0:
            return False

        form = form[0]

        text = self.parser.tocleanstring(form)
        m = re.search(u'(\d+) / (\d+)', text or '', flags=re.MULTILINE)
        if not m:
            return False

        cur = int(m.group(1))
        last = int(m.group(2))

        if cur == last:
            return False

        inputs = {}
        for elm in form.xpath('.//input[@type="input"]'):
            key = elm.attrib['name']
            value = elm.attrib['value']
            inputs[key] = value

        inputs['page'] = str(cur + 1)

        self.browser.location(form.attrib['action'], urllib.urlencode(inputs))

        return True

    def get_coming_link(self):
        try:
            a = self.parser.select(self.document, u'//a[contains(text(), "Opérations à venir")]', 1, 'xpath')
        except BrokenPageError:
            return None
        else:
            return a.attrib['href']


class ComingPage(OperationsPage):
    def get_history(self):
        index = 0
        for tr in self.document.xpath('//table[@class="liste"]/tbody/tr'):
            tds = tr.findall('td')
            if len(tds) < 3:
                continue

            tr = Transaction(index)

            date = self.parser.tocleanstring(tds[0])
            raw = self.parser.tocleanstring(tds[1])
            amount = self.parser.tocleanstring(tds[-1])

            tr.parse(date=date, raw=raw)
            tr.set_amount(amount)
            tr._is_coming = True
            yield tr


class CardPage(OperationsPage):
    def get_history(self):
        index = 0

        # Check if this is a multi-cards page
        pages = []
        for a in self.document.xpath('//table[@class="liste"]/tbody/tr/td/a'):
            card_link = a.get('href')
            history_url = 'https://%s/%s/fr/banque/%s' % (self.browser.DOMAIN, self.browser.currentSubBank, card_link)
            page = self.browser.get_document(self.browser.openurl(history_url))
            pages.append(page)

        if len(pages) == 0:
            # If not, add this page as transactions list
            pages.append(self.document)

        for page in pages:
            label = self.parser.tocleanstring(self.parser.select(page.getroot(), 'div.lister p.c', 1))
            label = re.findall('(\d+ [^ ]+ \d+)', label)[-1]
            # use the trick of relativedelta to get the last day of month.
            debit_date = parse_french_date(label) + relativedelta(day=31)

            for tr in page.xpath('//table[@class="liste"]/tbody/tr'):
                tds = tr.findall('td')[:4]
                if len(tds) < 4:
                    continue

                tr = Transaction(index)

                parts = [txt.strip() for txt in list(tds[-3].itertext()) + list(tds[-2].itertext()) if len(txt.strip()) > 0]

                tr.parse(date=tds[0].text.strip(' \xa0'),
                         raw=u' '.join(parts))
                tr.date = debit_date
                tr.type = tr.TYPE_CARD

                # Don't take all of the content (with tocleanstring for example),
                # because there is a span.aide.
                tr.set_amount(tds[-1].text)
                yield tr

class NoOperationsPage(OperationsPage):
    def get_history(self):
        return iter([])
