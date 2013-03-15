# -*- coding: utf-8 -*-

# Copyright(C) 2012-2013  Romain Bignon
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
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


__all__ = ['AccountsListPage', 'CPTHistoryPage', 'CardHistoryPage']


class AccountsListPage(BasePage):
    def get_list(self):
        accounts = []
        for tr in self.document.getiterator('tr'):
            tds = tr.findall('td')
            if len(tds) != 3 or tds[0].find('a') is None or tds[0].find('a').attrib.get('class', '') != 'flecheM':
                continue

            account = Account()
            account.id = tds[1].text.strip()

            a = tds[0].findall('a')[-1]
            account.label = unicode(a.text.strip())
            account._link_id = a.attrib['href']

            balance = u''.join([txt.strip() for txt in tds[2].itertext()])
            account.balance = Decimal(FrenchTransaction.clean_amount(balance))

            # check account type
            m = re.search('(\w+)_IdPrestation', account._link_id)
            account_type = None
            if m:
                account_type = m.group(1)
                if account_type != 'CPT':
                    account.id += '.%s' % account_type

            if account_type == 'CB':
                accounts[0]._card_links.append(account._link_id)
                if not accounts[0].coming:
                    accounts[0].coming = Decimal('0.0')
                accounts[0].coming += account.balance
                continue

            if account_type != 'CPT':
                # Don't support other kind of account histories.
                account._link_id = None

            account.currency = account.get_currency(tds[1].text)
            account._card_links = []

            accounts.append(account)

        return iter(accounts)


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^VIR(EMENT)? (?P<text>.*)'), FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^PRLV (?P<text>.*)'),        FrenchTransaction.TYPE_ORDER),
                (re.compile('^CB (?P<text>.*)\s+(?P<dd>\d+)/(?P<mm>\d+)\s*(?P<loc>.*)'),
                                                          FrenchTransaction.TYPE_CARD),
                (re.compile('^DAB (?P<dd>\d{2})/(?P<mm>\d{2}) ((?P<HH>\d{2})H(?P<MM>\d{2}) )?(?P<text>.*?)( CB N°.*)?$'),
                                                          FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^CHEQUE$'),                  FrenchTransaction.TYPE_CHECK),
                (re.compile('^COTIS\.? (?P<text>.*)'),    FrenchTransaction.TYPE_BANK),
                (re.compile('^REMISE (?P<text>.*)'),      FrenchTransaction.TYPE_DEPOSIT),
               ]


class HistoryPage(BasePage):
    def get_next_link(self):
        return None

    def get_operations(self, num_page, date_guesser):
        raise NotImplementedError()


class CPTHistoryPage(HistoryPage):
    def get_operations(self, num_page, date_guesser):
        for script in self.document.getiterator('script'):
            if script.text is None or script.text.find('\nCL(0') < 0:
                continue

            for m in re.finditer(r"CL\((\d+),'(.+)','(.+)','(.+)','([\d -\.,]+)',('([\d -\.,]+)',)?'\d+','\d+','[\w\s]+'\);", script.text, flags=re.MULTILINE):
                op = Transaction(m.group(1))
                op.parse(date=m.group(3), raw=re.sub(u'[ ]+', u' ', m.group(4).replace(u'\n', u' ')))
                op.set_amount(m.group(5))
                op._coming = (re.match('\d+/\d+/\d+', m.group(2)) is None)
                yield op


class CardHistoryPage(HistoryPage):
    def get_next_link(self):
        ok = False
        for link in self.document.xpath('//form[@name="FORM_LIB_CARTE"]/a[@class="fleche"]'):
            if link.attrib['href'].startswith('#'):
                ok = True
            elif ok:
                # add CB_IdPrestation to handle the correct page on browser.
                return link.attrib['href'] + '&CB_IdPrestation='

    def parse_date(self, guesser, string, store=False):
        day, month = map(int, string.split('/'))
        return guesser.guess_date(day, month, store)

    def get_operations(self, num_page, date_guesser):
        debit_date = None
        for tr in self.document.xpath('//div[@id="tabs-1"]/table//tr'):
            cols = tr.findall('td')
            if len(cols) == 1:
                text = self.parser.tocleanstring(cols[0])
                m = re.search('(\d+/\d+)', text)
                if m:
                    # if there are several months on the same page, the second
                    # one's operations are already debited.
                    if debit_date is not None:
                        num_page += 1
                    debit_date = self.parse_date(date_guesser, m.group(1), True)
                continue

            if len(cols) < 4:
                continue

            op = Transaction('')
            op.parse(date=debit_date,
                     raw=self.parser.tocleanstring(cols[1]))
            op.rdate = self.parse_date(date_guesser, self.parser.tocleanstring(cols[0]))
            op.type = op.TYPE_CARD
            op._coming = (num_page == 0)
            op.set_amount(self.parser.tocleanstring(cols[-1]),
                          self.parser.tocleanstring(cols[-2]))
            yield op
