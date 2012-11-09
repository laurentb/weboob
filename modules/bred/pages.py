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


from decimal import Decimal
import re

from weboob.tools.browser import BasePage
from weboob.tools.misc import to_unicode
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


__all__ = ['LoginPage', 'LoginResultPage', 'AccountsPage', 'TransactionsPage', 'EmptyPage']


class LoginPage(BasePage):
    def login(self, login, passwd):
        self.browser.select_form(name='authen')
        self.browser['id'] = login.encode(self.browser.ENCODING)
        self.browser['pass'] = passwd.encode(self.browser.ENCODING)
        self.browser.submit(nologin=True)

class LoginResultPage(BasePage):
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

            amount = sum([Decimal(txt.strip(' EUR').replace(' ', '').replace(',', '.')) for txt in cols[-1].itertext() if len(txt.strip()) > 0])
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

            account = Account()
            account.id = u'%s.%s' % (args['numero_compte'], args['numero_poste'])
            account.label = to_unicode(a.attrib.get('alt', a.text.strip()))
            account.balance = amount
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
                (re.compile('^.* LE (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2})$'),
                                                            FrenchTransaction.TYPE_UNKNOWN),
               ]


class TransactionsPage(BasePage):
    def get_history(self):
        is_coming = None

        for tr in self.document.xpath('//div[@class="scrollTbody"]/table//tr'):
            cols = tr.findall('td')

            # check if it's a card page, so by default transactions are not yet debited.
            if len(cols) == 6 and is_coming is None:
                is_coming = True

            col_label = cols[1]
            if col_label.find('a') is not None:
                col_label = col_label.find('a')

            date = u''.join([txt.strip() for txt in cols[0].itertext()])
            label = unicode(col_label.text.strip())

            # always strip card debits transactions. if we are on a card page, all next
            # transactions will be probably already debited.
            if label.startswith('DEBIT MENSUEL '):
                is_coming = False
                continue

            t = Transaction(col_label.attrib['id'])

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

            debit = u''.join([txt.strip() for txt in cols[-2].itertext()])
            credit = u''.join([txt.strip() for txt in cols[-1].itertext()])
            t.set_amount(credit, debit)

            t._is_coming = bool(is_coming)

            yield t
