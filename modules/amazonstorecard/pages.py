# -*- coding: utf-8 -*-

# Copyright(C) 2014-2015      Oleg Plakhotniuk
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

from weboob.capabilities.bank import Account, Transaction
from weboob.browser.pages import HTMLPage, RawPage, XMLPage
from weboob.tools.capabilities.bank.transactions import \
    AmericanTransaction as AmTr
from weboob.tools.date import closest_date
from weboob.tools.pdf import decompress_pdf
from weboob.tools.tokenizer import ReTokenizer
from datetime import datetime, timedelta


class SomePage(HTMLPage):
    @property
    def logged(self):
        return bool(self.doc.xpath('//span[@class="logoutBtn"]'))


class LoginPage(SomePage):
    INPUTS = ['userId', 'password', 'challengeAnswer1']

    is_here = '//form[@name="consumerLoginForm"]'

    def proceed(self, config):
        form = self.get_form(name='consumerLoginForm')
        for inp in (i for i in self.INPUTS if i in form):
            form[inp] = config[inp.lower()].get()
        form.submit()
        return self.browser.page


class SummaryPage(SomePage):
    DATA = {'subActionId': '1201', 'clientId': 'amazon',
            'accountType': 'plcc', 'langId': 'en'}

    def account(self):
        label = u' '.join(u''.join(self.doc.xpath(
            u'//text()[contains(.,"Account ending in")]')).split())
        balance = self.doc.xpath(
            '//span[@id="currentBalance"]/..')[0].text_content()
        a = Account()
        a.id = label[-4:]
        a.label = label
        a.currency = Account.get_currency(balance)
        a.balance = -AmTr.decimal_amount(balance)
        a.type = Account.TYPE_CARD
        return a


class RecentPage(XMLPage):
    DATA = {'subActionId': '1300', 'requestType': 'ajaxReq'}

    def iter_transactions(self):
        for ntrans in reversed(self.doc.xpath('//TRANSACTION')):
            desc = u' '.join(ntrans.xpath(
                'TRANSDESCRIPTION/text()')[0].split())
            tdate = u''.join(ntrans.xpath('TRANSACTIONDATE/text()'))
            pdate = u''.join(ntrans.xpath('POSTDATE/text()'))
            t = Transaction()
            t.date = datetime.strptime(tdate, '%m/%d/%Y')
            t.rdate = datetime.strptime(pdate or tdate, '%m/%d/%Y')
            t.type = Transaction.TYPE_UNKNOWN
            t.raw = desc
            t.label = desc
            t.amount = -AmTr.decimal_amount(ntrans.xpath('AMOUNT/text()')[0])
            yield t


class StatementsPage(SomePage):
    DATA = {'subActionId': '8168', 'clientId': 'amazon',
            'accountType': 'plcc', 'langId': 'en'}

    def iter_statements(self):
        for url in self.doc.xpath('//a[contains(@href,"ebillViewPDF")]/@href'):
            if url.endswith('inline=false'):
                self.browser.location(url)
                yield self.browser.page


class StatementPage(RawPage):
    LEX = [
        ('charge_amount', r'^\(\$([0-9\.]+)\) Tj$'),
        ('payment_amount', r'^\(\\\(\$([0-9\.]+)\\\)\) Tj$'),
        ('date', r'^\((\d+/\d+)\) Tj$'),
        ('full_date', r'^\((\d+/\d+/\d+)\) Tj$'),
        ('layout_td', r'^([-0-9]+ [-0-9]+) Td$'),
        ('ref', r'^\(([A-Z0-9]{17})\) Tj$'),
        ('text', r'^\((.*)\) Tj$')
    ]

    def __init__(self, *args, **kwArgs):
        RawPage.__init__(self, *args, **kwArgs)
        assert self.doc[:4] == '%PDF'
        self._pdf = decompress_pdf(self.doc)
        self._tok = ReTokenizer(self._pdf, '\n', self.LEX)

    def iter_transactions(self):
        return sorted(self.read_transactions(),
            cmp=lambda t1, t2: cmp(t2.date, t1.date) or
                               cmp(t1.label, t2.label) or
                               cmp(t1.amount, t2.amount))

    def read_transactions(self):
        # Statement typically cover one month.
        # Do 60 days, just to be on a safe side.
        date_to = self.read_closing_date()
        date_from = date_to - timedelta(days=60)

        pos = 0
        while not self._tok.tok(pos).is_eof():
            pos, trans = self.read_transaction(pos, date_from, date_to)
            if trans:
                yield trans
            else:
                pos += 1

    def read_transaction(self, pos, date_from, date_to):
        startPos = pos
        pos, tdate = self.read_date(pos)
        pos, pdate_layout = self.read_layout_td(pos)
        pos, pdate = self.read_date(pos)
        pos, ref_layout = self.read_layout_td(pos)
        pos, ref = self.read_ref(pos)
        pos, desc_layout = self.read_layout_td(pos)
        pos, desc = self.read_text(pos)
        pos, amount_layout = self.read_layout_td(pos)
        pos, amount = self.read_amount(pos)
        if tdate is None or pdate is None \
        or desc is None or amount is None or amount == 0:
            return startPos, None
        else:
            tdate = closest_date(tdate, date_from, date_to)
            pdate = closest_date(pdate, date_from, date_to)
            desc = u' '.join(desc.split())

            trans = Transaction(ref or u'')
            trans.date = tdate
            trans.rdate = pdate
            trans.type = Transaction.TYPE_UNKNOWN
            trans.raw = desc
            trans.label = desc
            trans.amount = amount
            return pos, trans

    def read_amount(self, pos):
        pos, ampay = self.read_payment_amount(pos)
        if ampay is not None:
            return pos, ampay
        return self.read_charge_amount(pos)

    def read_charge_amount(self, pos):
        t = self._tok.tok(pos)
        return (pos+1, -AmTr.decimal_amount(t.value())) \
            if t.is_charge_amount() else (pos, None)

    def read_payment_amount(self, pos):
        t = self._tok.tok(pos)
        return (pos+1, AmTr.decimal_amount(t.value())) \
            if t.is_payment_amount() else (pos, None)

    def read_closing_date(self):
        pos = 0
        while not self._tok.tok(pos).is_eof():
            pos, text = self.read_text(pos)
            if text == u'Statement Closing Date':
                break
            pos += 1
        while not self._tok.tok(pos).is_eof():
            pos, date = self.read_full_date(pos)
            if date is not None:
                return date
            pos += 1

    def read_text(self, pos):
        t = self._tok.tok(pos)
        return (pos+1, unicode(t.value())) \
            if t.is_text() else (pos, None)

    def read_full_date(self, pos):
        t = self._tok.tok(pos)
        return (pos+1, datetime.strptime(t.value(), '%m/%d/%Y')) \
            if t.is_full_date() else (pos, None)

    def read_date(self, pos):
        t = self._tok.tok(pos)
        return (pos+1, datetime.strptime(t.value(), '%m/%d')) \
            if t.is_date() else (pos, None)

    def read_ref(self, pos):
        t = self._tok.tok(pos)
        return (pos+1, t.value()) if t.is_ref() else (pos, None)

    def read_layout_td(self, pos):
        t = self._tok.tok(pos)
        return (pos+1, t.value()) if t.is_layout_td() else (pos, None)
