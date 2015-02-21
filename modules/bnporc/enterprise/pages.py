# -*- coding: utf-8 -*-

# Copyright(C) 2013      Laurent Bachelier
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
import hashlib
from urlparse import parse_qs
from datetime import datetime
import re

from weboob.capabilities.bank import Account
from weboob.deprecated.browser import Page, BrokenPageError
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.captcha.virtkeyboard import MappedVirtKeyboard, VirtKeyboardError
from weboob.tools.misc import to_unicode


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(u'^(?P<category>CHEQUE)(?P<text>.*)'),        FrenchTransaction.TYPE_CHECK),
                (re.compile('^(?P<category>FACTURE CARTE) DU (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) (?P<text>.*?)( CA?R?T?E? ?\d*X*\d*)?$'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile('^(?P<category>(PRELEVEMENT|TELEREGLEMENT|TIP)) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^(?P<category>ECHEANCEPRET)(?P<text>.*)'),   FrenchTransaction.TYPE_LOAN_PAYMENT),
                (re.compile('^(?P<category>RETRAIT DAB) (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2})( (?P<HH>\d+)H(?P<MM>\d+))? (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^(?P<category>VIR(EMEN)?T? ((RECU|FAVEUR) TIERS|SEPA RECU)?)( /FRM)?(?P<text>.*)'),
                                                            FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^(?P<category>REMBOURST) CB DU (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_PAYBACK),
                (re.compile('^(?P<category>REMBOURST)(?P<text>.*)'),     FrenchTransaction.TYPE_PAYBACK),
                (re.compile('^(?P<category>COMMISSIONS)(?P<text>.*)'),   FrenchTransaction.TYPE_BANK),
                (re.compile('^(?P<text>(?P<category>REMUNERATION).*)'),   FrenchTransaction.TYPE_BANK),
                (re.compile('^(?P<category>REMISE CHEQUES)(?P<text>.*)'), FrenchTransaction.TYPE_DEPOSIT),
               ]


class BEPage(Page):
    def get_error(self):
        for title in self.document.xpath('/html/head/title'):
            if 'erreur' in title.text or 'error' in title.text:
                return self.parser.select(self.document.getroot(),
                                          '//input[@name="titre_page"]', 1, 'xpath').value


class BNPVirtKeyboard(MappedVirtKeyboard):
    symbols = {'0': '97a2b5816f2db74851fe05afd17dc9fe',
               '1': '0a24fe3a35efeb0a89aa5e7b098e6842',
               '2': '65ff550debf85eacf8efaadd6cd80aa5',
               '3': '2bd67143fcd4207ac14d0ea8afdf4ebb',
               '4': 'a46bfd21636805a31a579b253c3b23d5',
               '5': '3f644894037255bc0feaba9abb1facfa',
               '6': '40d91064a749563fa4dd31fb52e880f0',
               '7': 'cd3af65da74d57df1e6a91ca946c09b7',
               '8': '85b718e032a02e887c757a7745a1f0bd',
               '9': 'c2cdc08c8c68855d83c0899d7e8c6719',
               '-1': 'd41d8cd98f00b204e9800998ecf8427e',
               }

    color = 45

    def __init__(self, basepage):
        img = basepage.document.find("//img[@usemap='#MapGril']")
        imgdata = basepage.browser.openurl(img.attrib['src'])
        MappedVirtKeyboard.__init__(self, imgdata, basepage.document, img, self.color)
        self.check_symbols(self.symbols, basepage.browser.responses_dirname)

    def get_symbol_coords(self, coords):
        # strip borders
        x1, y1, x2, y2 = coords
        return MappedVirtKeyboard.get_symbol_coords(self, (x1+6, y1+1, x2-6, y2-4))

    def get_symbol_code(self, md5sum):
        code = MappedVirtKeyboard.get_symbol_code(self, md5sum)
        code = code.split("'")[1]
        assert code.isdigit()
        return code

    def get_string_code(self, string):
        code = ''
        for c in string:
            code += self.get_symbol_code(self.symbols[c])
        return code

    def checksum(self, coords):
        """Copy of parent checksum(), but cropping (removes empty lines)"""
        x1, y1, x2, y2 = coords
        s = ''
        for y in range(y1, min(y2 + 1, self.height)):
            for x in range(x1, min(x2 + 1, self.width)):
                if self.check_color(self.pixar[x, y]):
                    s += " "
                else:
                    s += "O"
            s += "\n"
        s = '\n'.join([l for l in s.splitlines() if l.strip()])
        return hashlib.md5(s).hexdigest()


class LoginPage(BEPage):
    def login(self, login, password):
        try:
            vk = BNPVirtKeyboard(self)
        except VirtKeyboardError as err:
            self.logger.error("Error: %s" % err)
            return False

        self.browser.select_form(name='ident')
        self.browser.set_all_readonly(False)

        self.browser['ch1'] = login.encode('iso-8859-1')
        self.browser['chgrille'] = vk.get_string_code(password)
        self.browser.submit()


class AccountsPage(BEPage):
    def find_table(self):
        for table in self.parser.select(self.document.getroot(), 'table', 'many'):
            for td in self.parser.select(table, 'tr td'):
                if td.text and td.text.strip().startswith('COMPTES '):
                    return table

    def get_list(self):
        table = self.find_table()
        for tr in self.parser.select(table, 'tr', 'many'):
            tds = self.parser.select(tr, 'td')
            if len(tds) != 6:
                continue
            tdlabel, tdid, tdcur, tdupdated, tdbal, tdbalcur = tds

            account = Account()
            account.label = to_unicode(tdlabel.text_content().strip())
            # this is important - and is also the last part of the id (considering spaces)
            # we can't use only the link as it does not goes where we want
            try:
                link = self.parser.select(tdlabel, 'a', 1)
            except BrokenPageError:
                # probably an account we can't display the history
                account._link_id = None
            else:
                account._link_id = parse_qs(link.attrib['href'])['ch4'][0]
            account.id = to_unicode(tdid.text.strip().replace(' ', ''))
            account.iban = 'FR76' + account.id
            # just in case we are showing the converted balances
            account._main_currency = Account.get_currency(tdcur.text)
            # we have to ignore those accounts, because using NotAvailable
            # makes boobank and probably many others crash
            if tdbal.text_content().strip() == 'indisponible':
                continue
            account.balance = Decimal(Transaction.clean_amount(tdbal.text_content()))
            account.currency = Account.get_currency(tdbalcur.text)
            account._updated = datetime.strptime(tdupdated.text, '%d/%m/%Y')
            yield account


class HistoryPage(BEPage):
    def is_empty(self):
        for td in self.parser.select(self.document.getroot(), 'td.V11vertGras'):
            if u'Aucune opération enregistrée' in to_unicode(td.text_content()):
                return True
        return False

    def find_table(self):
        for table in self.parser.select(self.document.getroot(), 'table', 'many'):
            for td in self.parser.select(table, 'tr td'):
                if re.search('^OP.RATION', td.text_content().strip()):
                    return table

    def get_date_range(self):
        try:
            radio = self.parser.select(self.document, '//input[@name="br_tout_date"]', 1, 'xpath')
        except BrokenPageError:
            input = self.document.xpath('//input[@name="chB"]')[0]
            d1, d2 = re.findall('(\d+/\d+/\d+)', input.tail)
        else:
            d1 = radio.attrib['value'][0:10]
            d2 = radio.attrib['value'][10:20]
        return (d1, d2)

    TXT2CONST = {u'DATE VALEUR':    'vdate',
                 u'DATE D\'OPE':    'date',
                 u'OP.RATION':      'label',
                 u'D.BIT':          'debit',
                 u'CR.DIT':         'credit',
                }

    def iter_history(self):
        if self.is_empty():
            return

        columns = {'date': 0, 'vdate': 1, 'label': 2, 'debit': 3, 'credit': 4}

        table = self.find_table()
        for i, tr in enumerate(self.parser.select(table, 'tr', 'many')):
            tds = self.parser.select(tr, 'td')
            if len(tds) != 5:
                continue

            if self.parser.select(tr, 'td.thtitrefondbleu'):
                for i, td in enumerate(tds):
                    txt = self.parser.tocleanstring(td)
                    for part, const in self.TXT2CONST.iteritems():
                        if re.search(part, txt):
                            columns[const] = i
                            break
                continue

            tddate = self.parser.tocleanstring(tds[columns['date']])
            tdval = self.parser.tocleanstring(tds[columns['vdate']])
            tdlabel = self.parser.tocleanstring(tds[columns['label']])
            tddebit = self.parser.tocleanstring(tds[columns['debit']])
            tdcredit = self.parser.tocleanstring(tds[columns['credit']])

            if all((tddate, tdlabel, any((tddebit, tdcredit)))):
                if tddebit:
                    tdamount = '- %s' % tddebit
                else:
                    tdamount = tdcredit
                t = Transaction(i)
                t.set_amount(tdamount)
                t.parse(tddate, tdlabel, tdval)

                t._coming = (tds[0].find('span') is not None)

                yield t

    def get_next_numpage(self):
        current = 1
        m = re.search('chP=(\d+)', self.url)
        if m:
            current = int(m.group(1))

        try:
            pages = self.parser.tocleanstring(self.document.xpath('.//td[contains(text(), "Page")]')[0])
        except IndexError:
            # No pagination
            return None

        # We get list of all page numbers...
        pages = sorted(map(int, re.findall('(\d+)', pages)))

        try:
            # ...find position of the current page...
            curidx = pages.index(current)
        except ValueError:
            self.logger.warning('Unable to find the current page (%d)' % current)
            return None

        try:
            # ... and return number of the next page
            return pages[curidx+1]
        except IndexError:
            # Last page
            return None


class UnknownPage(BEPage):
    pass
