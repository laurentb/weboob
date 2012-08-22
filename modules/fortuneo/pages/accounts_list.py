# -*- coding: utf-8 -*-

# Copyright(C) 2012 Gilles-Alexandre Quenot
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
import datetime

from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import Transaction
from weboob.tools.browser import BasePage#, BrokenPageError
from weboob.capabilities import NotAvailable


__all__ = ['AccountsList', 'AccountHistoryPage']

class AccountHistoryPage(BasePage):
    def get_operations(self, _id):
        """history, see http://docs.weboob.org/api/capabilities/bank.html?highlight=transaction#weboob.capabilities.bank.Transaction"""

        # TODO need to rewrite that with FrenchTransaction class http://tinyurl.com/6lq4r9t
        operations = []
        tables = self.document.findall(".//*[@id='tabHistoriqueOperations']/tbody/tr")

        if len(tables) == 0:
            return []

        for i in range(len(tables)):
            operation = Transaction(len(operations))

            date_oper       = tables[i].xpath("./td[2]/text()")[0]
            date_val        = tables[i].xpath("./td[3]/text()")[0]
            label           = tables[i].xpath("./td[4]/text()")[0]
            operation.label = operation.raw = unicode(label.strip())
            amount          = tables[i].xpath("./td[5]/text() | ./td[6]/text()")
            operation.date  = datetime.datetime.strptime(date_val, "%d/%m/%Y")
            operation.rdate = datetime.datetime.strptime(date_oper,"%d/%m/%Y")
            operation.type  = 0

            if amount[1] == u'\xa0':
                amount = amount[0].replace(u"\xa0", "").replace(",", ".").strip()
            else:
                amount = amount[1].replace(u"\xa0", "").replace(",", ".").strip()
            operation.amount = Decimal(amount)

            operation.category  = NotAvailable

            operations.append(operation)

        return operations

class AccountsList(BasePage):
    def get_list(self):
        l = []

        for cpt in self.document.xpath(".//*[@class='synthese_id_compte']"):
            account = Account()

            # account.id
            account.id = cpt.xpath("./span/text()")[0].replace(u"\xa0", "").replace(',', '.').replace("EUR", "").replace("\n", "").replace("\t", "").replace(u"\xb0", '').replace(" ", "").replace('N', '')

            # account balance
            account.balance = Decimal(cpt.xpath("./span/text()")[1].replace("+", "").replace(u"\xa0", "").replace(',', '.').replace("EUR", "").replace("\n", "").replace("\t", "").replace(" ", ""))

            # account coming TODO
            #mycomingval = cpt.xpath("../../following-sibling::*[1]/td[2]/a[@class='lien_synthese_encours']/span/text()")[0].replace(',', '.').replace("EUR", "").replace("\n", "").replace("\t", "").replace(u"\xa0", "")
            #mycomingval = cpt.xpath("../../following-sibling::*[1]/td[2]")[0]
            #mycomingval = cpt.xpath("./../../../a[@class='lien_synthese_encours']/span[@class='synthese_encours']/text()")[0].replace(',', '.').replace("EUR", "").replace("\n", "").replace("\t", "").replace(u"\xa0", "")

            #if mycomingval == '-':
            #    account.coming = Decimal(0)
            #else:
            #    account.coming = Decimal(mycomingval)

            # account._link_id
            url_to_parse = cpt.xpath('@href')[0].replace("\n", "")  # link
            compte_id_re = re.compile(r'/prive/mes-comptes/([^/]+/).*COMPTE_ACTIF=([^\&]+)\&?')
            account._link_id = '/fr/prive/mes-comptes/%sconsulter-situation/consulter-solde.jsp?COMPTE_ACTIF=%s' % \
                    (compte_id_re.search(url_to_parse).groups()[0], compte_id_re.search(url_to_parse).groups()[1])

            # account.label
            account.label =  cpt.xpath("./span/text()")[0].replace(u"\xa0", "").replace(',', '.').replace("EUR", "").replace("\n", "").replace("\t", "").replace(" ", "").replace(u"\xb0", '').replace(" ", "").replace('N', '')

            l.append(account)

        return l

# vim:ts=4:sw=4
