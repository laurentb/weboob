# -*- coding: utf-8 -*-

# Copyright(C) 2011      Gabriel Kerneis
# Copyright(C) 2010-2011 Jocelyn Jaubert
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
from weboob.deprecated.browser import Page
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


class AccountsList(Page):
    def on_loaded(self):
        pass

    def get_list(self):
        blocks = self.document.xpath('//div[@id="synthese-list"]//div[@class="block"]')
        for div in blocks:
            block_title = ''.join(div.xpath('.//span[@class="title"]//text()')).lower()
            for tr in div.getiterator('tr'):
                account = Account()
                account.id = None
                account._link_id = None
                if 'assurance vie' in block_title:
                    # Life insurance accounts are investments
                    account.type = Account.TYPE_MARKET
                for td in tr.getiterator('td'):
                    if td.get('class', '') == 'account-cb':
                        try:
                            a = td.xpath('./*/a[@class="gras"]')[0]
                        except IndexError:
                            # ignore account
                            break
                        account.type = Account.TYPE_CARD
                        account.label = self.parser.tocleanstring(a)
                        try:
                            account._link_id = td.xpath('.//a')[0].get('href')
                        except KeyError:
                            pass

                    elif td.get('class', '') == 'account-name':
                        try:
                            span = td.xpath('./span[@class="label"]')[0]
                        except IndexError:
                            # ignore account
                            break
                        account.label = self.parser.tocleanstring(span)
                        try:
                            account._link_id = td.xpath('.//a')[0].get('href')
                            account._detail_url = account._link_id
                        except KeyError:
                            pass

                    elif td.get('class', '') == 'account-more-actions':
                        for a in td.getiterator('a'):
                            # For normal account, two "account-more-actions"
                            # One for the account, one for the credit card. Take the good one
                            if "mouvements.phtml" in a.get('href') and "/cartes/" not in a.get('href'):
                                account._link_id = a.get('href')

                    elif td.get('class', '') == 'account-number':
                        id = td.text
                        id = id.strip(u' \n\t')
                        account.id = id

                    elif td.get('class', '') == 'account-total':
                        span = td.find('span')
                        if span is None:
                            balance = td.text
                        else:
                            balance = span.text
                        account.currency = account.get_currency(balance)
                        balance = FrenchTransaction.clean_amount(balance)
                        if balance != "":
                            account.balance = Decimal(balance)
                        else:
                            account.balance = Decimal(0)

                else:
                    # because of some weird useless <tr>
                    if account.id is not None:
                        yield account
