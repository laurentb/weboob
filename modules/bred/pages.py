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


from mechanize import FormNotFoundError
from weboob.tools.mech import ClientForm
ControlNotFoundError = ClientForm.ControlNotFoundError

from decimal import Decimal, InvalidOperation
import re

from weboob.tools.browser import BasePage
from weboob.tools.misc import to_unicode
from weboob.tools.ordereddict import OrderedDict
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


class LoginPage(BasePage):
    def login(self, login, passwd):
        try:
            length = int(self.document.xpath('//input[@id="pass"]')[0].attrib['maxlength'])
        except (IndexError,KeyError):
            pass
        else:
            passwd = passwd[:length]

        self.browser.select_form(name='authen')
        try:
            self.browser['id'] = login.encode(self.browser.ENCODING)
            self.browser['pass'] = passwd.encode(self.browser.ENCODING)
        except ControlNotFoundError:
            self.browser.controls.append(ClientForm.TextControl('text', 'id', {'value': login.encode(self.browser.ENCODING)}))
            self.browser.controls.append(ClientForm.TextControl('text', 'pass', {'value': passwd.encode(self.browser.ENCODING)}))

        self.browser.submit(nologin=True)


class LoginResultPage(BasePage):
    def on_loaded(self):
        for script in self.document.xpath('//script'):
            text = script.text
            if text is None:
                continue
            m = re.search("window.location.replace\('([^']+)'\);", text)
            if m:
                self.browser.location(m.group(1))

        try:
            self.browser.select_form(name='banque')
        except FormNotFoundError:
            pass
        else:
            self.browser.set_all_readonly(False)
            accounts = OrderedDict()
            for tr in self.document.getroot().cssselect('table.compteTable > tbody > tr'):
                if len(tr.findall('td')) == 0:
                    continue
                attr = tr.xpath('.//a')[0].attrib.get('onclick', '')
                m = re.search("value = '(\w+)';(checkAndSubmit\('\w+','(\w+)','(\w+)'\))?", attr)
                if m:
                    typeCompte = m.group(1)
                    tagName = m.group(3)
                    if tagName is not None:
                        value = self.document.xpath('//input[@name="%s"]' % m.group(3))[int(m.group(4))].attrib['value']
                    else:
                        value = typeCompte
                    accounts[value] = (typeCompte, tagName)

            try:
                typeCompte, tagName = accounts[self.browser.accnum]
                value = self.browser.accnum
            except KeyError:
                accnums = ', '.join(accounts.keys())
                if self.browser.accnum != '00000000000':
                    self.logger.warning(u'Unable to find account "%s". Available ones: %s' % (self.browser.accnum, accnums))
                elif len(accounts) > 1:
                    self.logger.warning('There are several accounts, please use "accnum" backend parameter to force the one to use (%s)' % accnums)
                value, (typeCompte, tagName) = accounts.popitem(last=False)
            self.browser['typeCompte'] = typeCompte
            if tagName is not None:
                self.browser[tagName] = [value]
            self.browser.submit()

    def confirm(self):
        self.browser.location('MainAuth?typeDemande=AC', no_login=True)

    def get_error(self):
        error = self.document.xpath('//td[@class="txt_norm2"]')
        if len(error) == 0:
            return None

        error = error[0]
        if error.find('b') is not None:
            error = error.find('b')

        return error.text.strip()


class EmptyPage(BasePage):
    pass


class BredBasePage(BasePage):
    def js2args(self, s):
        cur_arg = None
        args = {}
        # For example:
        # javascript:reloadApplication('nom_application', 'compte_telechargement', 'numero_poste', '000', 'numero_compte', '12345678901','monnaie','EUR');
        for sub in re.findall("'([^']+)'", s):
            if cur_arg is None:
                cur_arg = sub
            else:
                args[cur_arg] = sub
                cur_arg = None

        return args


class AccountsPage(BredBasePage):
    def get_list(self):
        accounts = []

        for tr in self.document.xpath('//table[@class="compteTable"]/tr'):
            if not tr.attrib.get('class', '').startswith('ligne_'):
                continue

            cols = tr.findall('td')

            if len(cols) < 2:
                continue

            try:
                amount = sum([Decimal(FrenchTransaction.clean_amount(txt)) for txt in cols[-1].itertext() if len(txt.strip()) > 0])
            except InvalidOperation:
                continue

            a = cols[0].find('a')
            if a is None:
                # this line is a cards line. attach it on the first account.
                if len(accounts) == 0:
                    self.logger.warning('There is a card link but no accounts!')
                    continue

                for a in cols[0].xpath('.//li/a'):
                    args = self.js2args(a.attrib['href'])
                    if not 'numero_compte' in args or not 'numero_poste' in args:
                        self.logger.warning('Card link with strange args: %s' % args)
                        continue

                    accounts[0]._card_links.append('%s.%s' % (args['numero_compte'], args['numero_poste']))
                    if not accounts[0].coming:
                        accounts[0].coming = Decimal('0.0')
                    accounts[0].coming += amount
                continue

            args = self.js2args(a.attrib['href'])

            if not 'numero_compte' in args or not 'numero_poste' in args:
                self.logger.warning('Account link for %r with strange args: %s' % (a.attrib.get('alt', a.text), args))
                continue

            account = Account()
            account.id = u'%s.%s' % (args['numero_compte'], args['numero_poste'])
            account.label = to_unicode(a.attrib.get('alt', a.text.strip()))
            account.balance = amount
            account.currency = [account.get_currency(txt) for txt in cols[-1].itertext() if len(txt.strip()) > 0][0]
            account._card_links = []
            accounts.append(account)

        return accounts


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^RETRAIT G.A.B. \d+ (?P<text>.*?)( CARTE .*)? LE (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2}).*'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^VIR(EMENT)? (?P<text>.*)'),   FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^PRLV (?P<text>.*)'),          FrenchTransaction.TYPE_ORDER),
                (re.compile('^(?P<text>.*) TRANSACTION( CARTE .*)? LE (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2}) ?(.*)$'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile('^CHEQUE.*'),                   FrenchTransaction.TYPE_CHECK),
                (re.compile('^(CONVENTION \d+ )?COTISATION (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_BANK),
                (re.compile('^REMISE (?P<text>.*)'),        FrenchTransaction.TYPE_DEPOSIT),
                (re.compile('^(?P<text>.*)( \d+)? QUITTANCE .*'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^CB PAIEM. EN \d+ FOIS \d+ (?P<text>.*?) LE .* LE (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2})$'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile('^.* LE (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2})$'),
                                                            FrenchTransaction.TYPE_UNKNOWN),
               ]


class TransactionsPage(BasePage):
    def get_history(self, is_coming=None):
        last_debit = None
        transactions = []

        # check if it's a card page, so by default transactions are not yet debited.
        if len(self.document.xpath('//div[@class="scrollTbody"]/table//th')) == 6 and is_coming is None:
            is_coming = True

        for tr in self.document.xpath('//div[@class="scrollTbody"]/table//tr'):
            cols = tr.findall('td')

            if len(cols) < 4:
                continue

            col_label = cols[1]
            if col_label.find('a') is not None:
                col_label = col_label.find('a')

            date = self.parser.tocleanstring(cols[0])
            label = self.parser.tocleanstring(col_label)

            # always strip card debits transactions. if we are on a card page, all next
            # transactions will be probably already debited.
            if label.startswith('DEBIT MENSUEL '):
                is_coming = False
                continue

            t = Transaction(col_label.attrib.get('id', ''))

            # an optional tooltip on page contain the second part of the transaction label.
            tooltip = self.document.xpath('//div[@id="tooltip%s"]' % t.id)
            raw = label
            if len(tooltip) > 0:
                raw += u' ' + u' '.join([txt.strip() for txt in tooltip[0].itertext()])

            raw = re.sub(r'[ ]+', ' ', raw)

            t.parse(date, raw)

            # as only the first part of label is important to user, if there are no subpart
            # taken by FrenchTransaction regexps, reset the label as first part.
            if t.label == t.raw:
                t.label = label

            debit = self.parser.tocleanstring(cols[-2])
            credit = self.parser.tocleanstring(cols[-1])
            t.set_amount(credit, debit)

            if 'CUMUL DES DEPENSES CARTES BANCAIRES REGLEES' in t.raw:
                if last_debit is None:
                    last_debit = t.date
                continue

            t._is_coming = bool(is_coming)

            # If this is a card, get the right debit date (rdate is already set
            # with the operation date with t.parse())
            if is_coming is not None:
                t.date = t.parse_date(self.parser.tocleanstring(cols[-3]))

            transactions.append(t)

        if last_debit is not None and is_coming is True:
            for tr in transactions:
                if tr.date <= last_debit.replace(day=1):
                    tr._is_coming = False

        return iter(transactions)
