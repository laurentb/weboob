# -*- coding: utf-8 -*-

# Copyright(C) 2009-2011  Romain Bignon
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

from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.capabilities.bank import Account
from weboob.capabilities.base import NotAvailable
from weboob.deprecated.browser import Page, BrokenPageError, BrowserPasswordExpired


class AccountsList(Page):
    ACCOUNT_TYPES = {
        u'Liquidités': Account.TYPE_CHECKING,
        u'Epargne disponible': Account.TYPE_SAVINGS,
        u'Titres': Account.TYPE_MARKET,
        u'Assurance vie': Account.TYPE_DEPOSIT,
        u'Crédit immobilier': Account.TYPE_LOAN,
    }

    def on_loaded(self):
        pass

    def _parse_iban(self, account, url):
        m = re.search('ch4=(\w+)', url)
        if m:
            account.iban = unicode(m.group(1))

    def _parse_account_group(self, table):
        typename = unicode(table.attrib.get('summary', '').replace('Liste des contrats/comptes ', ''))
        typeid = self.ACCOUNT_TYPES.get(typename, Account.TYPE_UNKNOWN)
        account = None
        for tr in table.xpath('.//tr'):
            if tr.find('td') is not None and tr.find('td').attrib.get('class', '') == 'typeTitulaire':
                account = self._parse_account(tr)
                account.type = typeid
                yield account
            elif tr.get('class', '') == 'listeActionBig' and account is not None:
                try:
                    url = tr.xpath('.//a')[-1].get('href', '')
                except IndexError:
                    pass
                else:
                    self._parse_iban(account, url)
                account = None

    def _parse_account(self, tr):
        account = Account()

        # for pro usage
        account._stp = None

        account.id = tr.xpath('.//td[@class="libelleCompte"]/input')[0].attrib['id'][len('libelleCompte'):]
        if len(str(account.id)) == 23:
            account.id = str(account.id)[5:21]

        a = tr.xpath('.//td[@class="libelleCompte"]/a')[0]
        m = re.match(r'javascript:goToStatements\(\'(\d+)\'', a.get('onclick', ''))
        if m:
            account._link_id = m.group(1)
        else:
            # Can't get history for this account.
            account._link_id = None
            # To prevent multiple-IDs for CIF (for example), add an arbitrary char in ID.
            account.id += 'C'

        account.label = u''+a.text.strip()

        tds = tr.findall('td')
        account.currency = account.get_currency(tds[3].find('a').text)
        account.balance = self._parse_amount(tds[3].find('a'))
        if tds[4].find('a') is not None:
            account.coming = self._parse_amount(tds[4].find('a'))
        else:
            account.coming = NotAvailable

        return account

    def _parse_amount(self, elem):
        return Decimal(FrenchTransaction.clean_amount(elem.text))

    def get_list(self):
        accounts = []
        for table in self.document.xpath('//table[@class="tableCompte"]'):
            for account in self._parse_account_group(table):
                accounts.append(account)

        if len(accounts) == 0:
            # oops, no accounts? check if we have not exhausted the allowed use
            # of this password
            for img in self.document.getroot().cssselect('img[align="middle"]'):
                if img.attrib.get('alt', '') == 'Changez votre code secret':
                    raise BrowserPasswordExpired('Your password has expired')
        return accounts

    def get_execution_id(self):
        return self.document.xpath('//input[@name="_flowExecutionKey"]')[0].attrib['value']

    def get_messages_link(self):
        """
        Get the link to the messages page, which seems to have an identifier in it.
        """
        for link in self.parser.select(self.document.getroot(), 'div#pantalon div.interieur a'):
            if 'MessagesRecus' in link.attrib.get('href', ''):
                return link.attrib['href']
        raise BrokenPageError('Unable to find the link to the messages page')


class AccountPrelevement(AccountsList):
    pass
