# -*- coding: utf-8 -*-

# Copyright(C) 2012 Kevin Pouget, based on Romain Bignon work
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


from urlparse import urlsplit, parse_qsl
from decimal import Decimal
import re

from weboob.tools.browser import BasePage
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


__all__ = ['LoginPage', 'AccountsPage']

class LoginPage(BasePage):
    def login(self, login, pin):
        self.browser.select_form(name='loginCoForm', nr=1)
        self.browser['codeUtil'] = login
        self.browser['motPasse'] = pin

        assert self.browser['identType'] == "RENFORCE"
        self.browser.submit(nologin=True)

class AccountsPage(BasePage):
    ACCOUNT_TYPES = {u'COMPTE NEF': Account.TYPE_CHECKING
                    }
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
        for tbCompte in self.document.xpath('//table[@id="compte"]'):
            for trCompte in tbCompte.xpath('.//tbody/tr'):
                tds = trCompte.findall('td')

                account = Account()
                
                account.id = tds[self.CPT_ROW_ID].text.strip()
                account.label = tds[self.CPT_ROW_NAME].text.strip()

                account_type_str = "".join([td.text for td in tds[self.CPT_ROW_NATURE].xpath('.//td[@class="txt"]')]).strip()

                account.type = self.ACCOUNT_TYPES.get(account_type_str,  Account.TYPE_UNKNOWN)

                account.balance = Decimal(FrenchTransaction.clean_amount(tds[self.CPT_ROW_BALANCE].find("a").text))
                account.coming = Decimal(FrenchTransaction.clean_amount( tds[self.CPT_ROW_ENCOURS].find("a").text))
                yield account

        return

class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^RET DAB (?P<text>.*?) RETRAIT DU (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}).*'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^RET DAB (?P<text>.*?) CARTE ?:.*'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^(?P<text>.*) RETRAIT DU (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) .*'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('(\w+) (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) CB:[^ ]+ (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile('^VIR(EMENT)? (?P<text>.*)'),   FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^PRLV (?P<text>.*)'),          FrenchTransaction.TYPE_ORDER),
                (re.compile('^CHEQUE.*'),                   FrenchTransaction.TYPE_CHECK),
                (re.compile('^(AGIOS /|FRAIS) (?P<text>.*)'),       FrenchTransaction.TYPE_BANK),
                (re.compile('^(CONVENTION \d+ )?COTIS(ATION)? (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_BANK),
                (re.compile('^REMISE (?P<text>.*)'),        FrenchTransaction.TYPE_DEPOSIT),
                (re.compile('^(?P<text>.*)( \d+)? QUITTANCE .*'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^.* LE (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2})$'),
                                                            FrenchTransaction.TYPE_UNKNOWN),
               ]


class TransactionsPage(BasePage):
    def get_next_params(self):
        if len(self.document.xpath('//li[@id="tbl1_nxt"]')) == 0:
            return None

        params = {}
        for field in self.document.xpath('//input'):
            params[field.attrib['name']] = field.attrib.get('value', '')

        params['validationStrategy'] = 'NV'
        params['pagingDirection'] = 'NEXT'
        params['pagerName'] = 'tbl1'

        return params

    TRA_ROW_DT_OP = 0
    TRA_ROW_DT_VAL = 1
    TRA_ROW_NAME = 3
    TRA_ROW_DEBIT = 4
    TRA_ROW_CREDIT = 5
    
    def get_history(self):
        for tr in self.document.xpath('//table[@id="operation"]/tbody/tr'):
            import pdb;pdb.set_trace()
            tds = tr.findall('td')

            def get_content(td):
                ret = "".join([ttd.text for ttd in td.xpath(".//td")])
                return ret.replace("&nbsp;", " ").strip()
                               
            t = Transaction(tr.attrib['id'].split('_', 1)[1])
            date = u''.join([txt.strip() for txt in tds[4].itertext()])
            raw = u' '.join([txt.strip() for txt in tds[1].itertext()])
            debit = u''.join([txt.strip() for txt in tds[-2].itertext()])
            credit = u''.join([txt.strip() for txt in tds[-1].itertext()])
            t.parse(date, re.sub(r'[ ]+', ' ', raw))
            t.set_amount(credit, debit)
            yield t
