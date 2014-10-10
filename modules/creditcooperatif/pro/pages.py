# -*- coding: utf-8 -*-

# Copyright(C) 2012 Kevin Pouget
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
import time

from weboob.deprecated.browser import Page
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


class LoginPage(Page):
    def login(self, login, pin, strong_auth):
        form_nb = 1 if strong_auth else 0
        indentType = "RENFORCE" if strong_auth else "MDP"

        self.browser.select_form(name='loginCoForm', nr=form_nb)
        self.browser['codeUtil'] = login.encode(self.browser.ENCODING)
        self.browser['motPasse'] = pin.encode(self.browser.ENCODING)

        assert self.browser['identType'] == indentType
        self.browser.submit(nologin=True)


class AccountsPage(Page):
    ACCOUNT_TYPES = {u'COMPTE NEF': Account.TYPE_CHECKING}

    CPT_ROW_ID = 0
    CPT_ROW_NAME = 1
    CPT_ROW_NATURE = 2
    CPT_ROW_BALANCE = 3
    CPT_ROW_ENCOURS = 4

    def is_error(self):
        for par in self.document.xpath('//p[@class=acctxtnoirlien]'):
            if par.text is not None and u"La page demandée ne peut pas être affichée." in par.text:
                return True

        return False

    def get_list(self):
        for trCompte in self.document.xpath('//table[@id="compte"]/tbody/tr'):
            tds = trCompte.findall('td')

            account = Account()

            account.id = tds[self.CPT_ROW_ID].text.strip()
            account.label = unicode(tds[self.CPT_ROW_NAME].text.strip())

            account_type_str = "".join([td.text for td in tds[self.CPT_ROW_NATURE].xpath('.//td[@class="txt"]')]).strip()

            account.type = self.ACCOUNT_TYPES.get(account_type_str,  Account.TYPE_UNKNOWN)

            account.balance = Decimal(FrenchTransaction.clean_amount(self.parser.tocleanstring(tds[self.CPT_ROW_BALANCE])))
            account.coming = Decimal(FrenchTransaction.clean_amount(self.parser.tocleanstring( tds[self.CPT_ROW_ENCOURS])))
            account.currency = account.get_currency(tds[self.CPT_ROW_BALANCE].find("a").text)
            yield account

        return


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^RETRAIT DAB (?P<text>.*?).*'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^(?P<text>.*) RETRAIT DU (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) .*'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^CARTE \d+ .*'),               FrenchTransaction.TYPE_CARD),
                (re.compile('^VIR(EMENT)? (?P<text>.*)'),   FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^(PRLV|PRELEVEMENT) (?P<text>.*)'),          FrenchTransaction.TYPE_ORDER),
                (re.compile('^CHEQUE.*'),                   FrenchTransaction.TYPE_CHECK),
                (re.compile('^(AGIOS /|FRAIS) (?P<text>.*)'),       FrenchTransaction.TYPE_BANK),
                (re.compile('^ABONNEMENT (?P<text>.*)'),    FrenchTransaction.TYPE_BANK),
                (re.compile('^REMISE (?P<text>.*)'),        FrenchTransaction.TYPE_DEPOSIT),
                (re.compile('^(?P<text>.*)( \d+)? QUITTANCE .*'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^.* LE (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2})$'),
                                                            FrenchTransaction.TYPE_UNKNOWN),
               ]


class ITransactionsPage(Page):
    def get_next_url(self):
        # can be 'Suivant' or ' Suivant'
        next = self.document.xpath("//a[normalize-space(text()) = 'Suivant']")

        if not next:
            return None

        return next[0].attrib["href"]

    def get_history(self):
        raise NotImplementedError()


class TransactionsPage(ITransactionsPage):
    TR_DATE = 0
    TR_TEXT = 2
    TR_DEBIT = 3
    TR_CREDIT = 4
    TABLE_NAME = 'operation'

    def get_history(self):
        for tr in self.document.xpath('//table[@id="%s"]/tbody/tr' % self.TABLE_NAME):
            tds = tr.findall('td')

            def get_content(td):
                ret = self.parser.tocleanstring(td)
                return ret.replace(u"\xa0", " ").strip()

            date = get_content(tds[self.TR_DATE])
            raw = get_content(tds[self.TR_TEXT])

            debit = get_content(tds[self.TR_DEBIT])
            credit = get_content(tds[self.TR_CREDIT])

            t = Transaction(date+""+raw)
            t.parse(date, re.sub(r'[ ]+', ' ', raw))
            t.set_amount(credit, debit)

            yield t


class ComingTransactionsPage(TransactionsPage):
    TR_DATE = 2
    TR_TEXT = 1
    TR_DEBIT = -2
    TR_CREDIT = -1
    TABLE_NAME = 'operationAVenir'


class CardTransactionsPage(ITransactionsPage):
    COM_TR_COMMENT = 0
    COM_TR_DATE = 1
    COM_TR_TEXT = 2
    COM_TR_VALUE = 3

    def get_history(self):
        comment = None
        for tr in self.document.xpath('//table[@id="operation"]/tbody/tr'):
            tds = tr.findall('td')

            def get_content(td):
                ret = td.text
                return ret.replace(u"\xa0", " ").strip()

            raw = get_content(tds[self.COM_TR_TEXT])

            if comment is None:
                comment = get_content(tds[self.COM_TR_COMMENT])
                raw = "%s (%s) " % (raw, comment)

            debit = get_content(tds[self.COM_TR_VALUE])
            date = get_content(tds[self.COM_TR_DATE])

            if comment is not None:
                #date is 'JJ/MM'. add '/YYYY'
                date += comment[comment.rindex("/"):]
            else:
                date += "/%d" % time.localtime().tm_year

            t = Transaction(date+""+raw)
            t.parse(date, re.sub(r'[ ]+', ' ', raw))
            t.set_amount("", debit)

            yield t
