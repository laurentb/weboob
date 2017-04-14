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
import requests
import ast

from weboob.browser.pages import HTMLPage, pagination
from weboob.browser.elements import method
from weboob.browser.filters.standard import Env
from weboob.browser.filters.html import Attr
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


class LoginPage(HTMLPage):
    def login(self, login, passwd):
        tab = re.search(r'tab = (\[[\d,\s]*\])', self.content).group(1)
        number_list = ast.literal_eval(tab)
        key_map = {}
        for i, number in enumerate(number_list):
            if number < 10:
                key_map[number] = chr(ord('A') + i)
        pass_string = ''.join(key_map[int(n)] for n in passwd)
        form = self.get_form(name='loginForm')
        form['username'] = login
        form['password'] = pass_string
        form.submit()


class AccountsPage(HTMLPage):
    logged = True
    ACCOUNT_TYPES = {u'Solde des comptes bancaires - Groupama Banque':  Account.TYPE_CHECKING,
                     u'Epargne bancaire constituée - Groupama Banque':  Account.TYPE_SAVINGS,
                    }

    def get_list(self):
        account_type = Account.TYPE_UNKNOWN
        accounts = []

        for tr in self.doc.xpath('//div[@class="finance"]/form/table[@class="ecli"]/tr'):
            if tr.attrib.get('class', '') == 'entete':
                account_type = self.ACCOUNT_TYPES.get(tr.find('th').text.strip(), Account.TYPE_UNKNOWN)
                continue

            tds = tr.findall('td')

            balance = tds[-1].text.strip()
            if balance == '':
                continue

            account = Account()
            account.label = u' '.join([txt.strip() for txt in tds[0].itertext()])
            account.label = re.sub(u'[ \xa0\u2022\r\n\t]+', u' ', account.label).strip()
            account.id = re.findall('(\d+)', account.label)[0]
            account.balance = Decimal(FrenchTransaction.clean_amount(balance))
            account.currency = account.get_currency(balance)
            account.type = account_type
            m = re.search(r"javascript:submitForm\(([\w_]+),'([^']+)'\);", tds[0].find('a').attrib['onclick'])
            if not m:
                self.logger.warning('Unable to find link for %r' % account.label)
                account._link = None
            else:
                account._link = m.group(2)

            accounts.append(account)

        return accounts


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^Facture (?P<dd>\d{2})/(?P<mm>\d{2})-(?P<text>.*) carte .*'),
                                                                FrenchTransaction.TYPE_CARD),
                (re.compile(u'^(Prlv( de)?|Ech(éance|\.)) (?P<text>.*)'),
                                                                FrenchTransaction.TYPE_ORDER),
                (re.compile('^(Vir|VIR)( de)? (?P<text>.*)'),
                                                                FrenchTransaction.TYPE_TRANSFER),
                (re.compile(u'^CHEQUE.*? (N° \w+)?$'),          FrenchTransaction.TYPE_CHECK),
                (re.compile('^Cotis(ation)? (?P<text>.*)'),
                                                                FrenchTransaction.TYPE_BANK),
                (re.compile('(?P<text>Int .*)'),                FrenchTransaction.TYPE_BANK),
               ]


class TransactionsPage(HTMLPage):
    logged = True

    @pagination
    @method
    class get_history(Transaction.TransactionsElement):
        head_xpath = '//table[@id="releve_operation"]//tr/th'
        item_xpath = '//table[@id="releve_operation"]//tr'

        col_date =       [u'Date opé', 'Date', u'Date d\'opé', u'Date opération']
        col_vdate =      [u'Date valeur']
        col_credit =     [u'Crédit', u'Montant', u'Valeur']
        col_debit =      [u'Débit']

        def next_page(self):
            url = Attr('//a[contains(text(), "Page suivante")]', 'onclick', default=None)(self)
            if url:
                m = re.search('\'([^\']+).*([\d]+)', url)
                return requests.Request("POST", m.group(1), data={'numCompte': Env('accid')(self), \
                                        'vue': "ReleveOperations", 'tri': "DateOperation", 'sens': \
                                        "DESC", 'page': m.group(2), 'nb_element': "25"})

        class item(Transaction.TransactionElement):
            def condition(self):
                return len(self.el.xpath('./td')) > 3

    def get_coming_link(self):
        try:
            a = self.doc.getroot().cssselect('div#sous_nav ul li a.bt_sans_off')[0]
        except IndexError:
            return None
        return re.sub('[ \t\r\n]+', '', a.attrib['href'])


