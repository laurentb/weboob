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
from datetime import date as ddate, timedelta

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.filters.standard import CleanText
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.date import parse_date
from weboob.tools.compat import unicode


class TechnicalErrorPage(LoggedPage, HTMLPage):
    pass


class LoginPage(HTMLPage):
    def login(self, login, pin, strong_auth):
        form_nb = 1 if strong_auth else 0
        indentType = "RENFORCE" if strong_auth else "MDP"

        form = self.get_form(name='loginCoForm', nr=form_nb)
        form['codeUtil'] = login
        form['motPasse'] = pin[:12]

        assert form['identType'] == indentType
        form.submit()


class AccountsPage(LoggedPage, HTMLPage):
    ACCOUNT_TYPES = {u'COMPTE NEF': Account.TYPE_CHECKING}

    CPT_ROW_ID = 0
    CPT_ROW_NAME = 1
    CPT_ROW_NATURE = 2
    CPT_ROW_BALANCE = 3
    CPT_ROW_ENCOURS = 4

    def is_error(self):
        for par in self.doc.xpath('//p[@class=acctxtnoirlien]'):
            if par.text is not None and u"La page demandée ne peut pas être affichée." in par.text:
                return True

        return False

    def get_list(self):
        for trCompte in self.doc.xpath('//table[@id="compte"]/tbody/tr'):
            tds = trCompte.findall('td')

            account = Account()

            account.id = tds[self.CPT_ROW_ID].text.strip()
            account.label = unicode(tds[self.CPT_ROW_NAME].text.strip())
            account_type_str = "".join([td.text for td in tds[self.CPT_ROW_NATURE].xpath('.//td[@class="txt" and @width="99%"]')]).strip()

            account.type = self.ACCOUNT_TYPES.get(account_type_str,  Account.TYPE_UNKNOWN)

            cleaner = CleanText('.')
            account.balance = Decimal(FrenchTransaction.clean_amount(cleaner(tds[self.CPT_ROW_BALANCE])))
            account.coming = Decimal(FrenchTransaction.clean_amount(cleaner(tds[self.CPT_ROW_ENCOURS])))
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


class ITransactionsPage(LoggedPage, HTMLPage):
    def get_next_url(self):
        # can be 'Suivant' or ' Suivant'
        next = self.doc.xpath("//a[normalize-space(text()) = 'Suivant']")

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
        for tr in self.doc.xpath('//table[@id=$id]/tbody/tr', id=self.TABLE_NAME):
            tds = tr.findall('td')

            get_content = CleanText('.')

            date = get_content(tds[self.TR_DATE])
            raw = get_content(tds[self.TR_TEXT])

            debit = get_content(tds[self.TR_DEBIT])
            credit = get_content(tds[self.TR_CREDIT])

            t = Transaction()
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
        if self.doc.xpath(u'//table[@id="operation"]/thead//th[text()[contains(.,"Numéro carte")]]'):
            self.logger.debug('multiple cards on same account')
            for a in self.doc.xpath(u'//table[@id="operation"]/tbody//a[contains(@href,"/banque/cpt/cpt/encourscartesbancaires.do")]/@href'):
                page = self.browser.open(a).page
                for tr in page.get_single_history():
                    yield tr
            return

        for tr in self.get_single_history():
            yield tr

    def get_single_history(self):
        now = ddate.today()
        delta = timedelta(days=60) # random duration

        debit_date = None
        for tr in self.doc.xpath('//table[@id="operation"]/tbody/tr'):
            tds = tr.findall('td')

            get_content = CleanText('.', children=False)

            raw = get_content(tds[self.COM_TR_TEXT])

            comment = get_content(tds[self.COM_TR_COMMENT])
            if comment:
                debit_date = re.sub(u'Débit au ', '', comment)

            debit = get_content(tds[self.COM_TR_VALUE])
            date = parse_date(get_content(tds[self.COM_TR_DATE]))
            if date > now + delta:
                date = date.replace(year=date.year - 1)
            elif date < now - delta:
                date = date.replace(year=date.year + 1)

            t = Transaction()
            t.parse(debit_date or date, re.sub(r'[ ]+', ' ', raw), vdate=date)
            t.rdate = t.vdate or t.date
            t.set_amount("", debit)

            yield t
