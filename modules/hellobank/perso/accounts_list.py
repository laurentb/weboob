# -*- coding: utf-8 -*-

# Copyright(C) 2013 Christophe Lampin
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

from decimal import Decimal

from weboob.capabilities.bank import Account
from weboob.deprecated.browser import Page, BrowserPasswordExpired
from weboob.tools.json import json


class AccountsList(Page):
    ACCOUNT_TYPES = {
        1: Account.TYPE_CHECKING,
        2: Account.TYPE_SAVINGS,
        3: Account.TYPE_DEPOSIT,
        5: Account.TYPE_LIFE_INSURANCE,
        8: Account.TYPE_LOAN,
        9: Account.TYPE_LOAN,
    }

    def on_loaded(self):
        pass

    def get_list(self, accounts_ids):
        l = []
        # Read the json data
        json_data = self.browser.readurl('/banque/PA_Autonomy-war/ProxyIAService?cleOutil=IA_SMC_UDC&service=getlstcpt&dashboard=true&refreshSession=true&cre=udc&poka=true')
        json_infos = json.loads(json_data)
        for famille in json_infos['smc']['data']['familleCompte']:
            id_famille = famille['idFamilleCompte']
            for compte in famille['compte']:
                account = Account()
                account.label = unicode(compte['libellePersoProduit'] or compte['libelleProduit'])
                account.currency = account.get_currency(compte['devise'])
                account.balance = Decimal(str(compte['soldeDispo']))
                account.coming = Decimal(str(compte['soldeAVenir']))
                account.type = self.ACCOUNT_TYPES.get(id_famille, Account.TYPE_UNKNOWN)
                account.id = None
                if account.type != Account.TYPE_LIFE_INSURANCE:
                    account._link_id = 'KEY'+compte['key']
                else:
                    account._link_id = None

                # IBAN aren't in JSON
                # Fast method, get it from transfer page.
                for i,a in accounts_ids.items():
                    if a.label == account.label:
                        account.id = i
                # But it's doesn't work with LOAN and MARKET, so use slow method : Get it from transaction page.
                if account.id is None:
                    if account._link_id:
                        self.logger.debug('Get IBAN for account %s', account.label)
                        account.id = self.browser.get_IBAN_from_account(account)
                    else:
                        account.id = compte['value']

                l.append(account)

        if len(l) == 0:
            self.logger.warning('no accounts')
            # oops, no accounts? check if we have not exhausted the allowed use
            # of this password
            for img in self.document.getroot().cssselect('img[align="middle"]'):
                if img.attrib.get('alt', '') == 'Changez votre code secret':
                    raise BrowserPasswordExpired('Your password has expired')
        return l

    def get_execution_id(self):
        return self.document.xpath('//input[@name="_flowExecutionKey"]')[0].attrib['value']

    def get_messages_link(self):
        """
        Get the link to the messages page, which seems to have an identifier in it.
        """
        return self.document.xpath('//a[@title="Messagerie"]')[0].attrib['href']


class AccountPrelevement(AccountsList):
    pass
