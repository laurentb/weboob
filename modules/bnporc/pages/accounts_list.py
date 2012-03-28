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


from weboob.capabilities.bank import Account
from weboob.capabilities.base import NotAvailable
from weboob.tools.browser import BasePage, BrokenPageError

from ..errors import PasswordExpired


__all__ = ['AccountsList']


class AccountsList(BasePage):
    ACCOUNT_TYPES = {
        u'Liquidités': Account.TYPE_CHECKING,
        u'Epargne disponible': Account.TYPE_SAVINGS,
        u'Titres': Account.TYPE_MARKET,
        u'Assurance vie': Account.TYPE_DEPOSIT,
        u'Crédit immobilier': Account.TYPE_LOAN,
    }

    def on_loaded(self):
        pass

    def _parse_account_group(self, table):
        typename = unicode(table.attrib.get('summary', '').replace('Liste des contrats/comptes ', ''))
        typeid = self.ACCOUNT_TYPES.get(typename, Account.TYPE_UNKNOWN)
        for tr in table.xpath('.//tr[not(@class)]'):
            if tr.find('td') is not None and tr.find('td').attrib.get('class', '') == 'typeTitulaire':
                account = self._parse_account(tr)
                account.type = typeid
                yield account

    def _parse_account(self, tr):
        account = Account()
        account.id = tr.xpath('.//td[@class="libelleCompte"]/input')[0].attrib['id'][len('libelleCompte'):]
        account._link_id = account.id
        if len(str(account.id)) == 23:
            account.id = str(account.id)[5:21]

        account.label = u''+tr.xpath('.//td[@class="libelleCompte"]/a')[0].text.strip()

        tds = tr.findall('td')
        account.balance = self._parse_amount(tds[3].find('a'))
        if tds[4].find('a') is not None:
            account.coming = self._parse_amount(tds[4].find('a'))
        else:
            account.coming = NotAvailable

        return account

    def _parse_amount(self, elem):
        return float(elem.text.replace('.', '').replace(',', '.').strip(u' \t\u20ac\xa0€\n\r'))

    def get_list(self):
        l = []
        for table in self.document.xpath('//table[@class="tableCompte"]'):
            for account in self._parse_account_group(table):
                l.append(account)

        if len(l) == 0:
            # oops, no accounts? check if we have not exhausted the allowed use
            # of this password
            for img in self.document.getroot().cssselect('img[align="middle"]'):
                if img.attrib.get('alt', '') == 'Changez votre code secret':
                    raise PasswordExpired('Your password has expired')
        return l

    def get_execution_id(self):
        return self.document.xpath('//input[@name="execution"]')[0].attrib['value']

    def get_messages_link(self):
        """
        Get the link to the messages page, which seems to have an identifier in it.
        """
        for link in self.parser.select(self.document.getroot(), 'div#pantalon div.interieur a'):
            if 'MessagesRecus' in link.attrib.get('href', ''):
                return link.attrib['href']
        raise BrokenPageError('Unable to find the link to the messages page')
