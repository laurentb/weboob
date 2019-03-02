# -*- coding: utf-8 -*-

# Copyright(C) 2014-2015      Oleg Plakhotniuk
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from weboob.capabilities.bank import Account, Transaction
from weboob.browser.exceptions import ServerError
from weboob.browser.pages import HTMLPage, RawPage
from weboob.tools.capabilities.bank.transactions import \
    AmericanTransaction as AmTr
from weboob.tools.date import closest_date
from weboob.tools.pdf import decompress_pdf
from weboob.tools.tokenizer import ReTokenizer
from datetime import datetime, timedelta
from weboob.tools.compat import unicode
import re
import json


try:
    cmp = cmp
except NameError:
    def cmp(x, y):
        return (x > y) - (x < y)


class SomePage(HTMLPage):
    @property
    def logged(self):
        return bool(self.doc.xpath(u'//a[text()="Logout"]'))


class SummaryPage(SomePage):
    def account(self):
        label = u' '.join(self.doc.xpath(
            '//div[contains(@class,"myCreditCardDetails")]')[0]
            .text_content().split())
        balance = self.amount(u'Balance')
        cardlimit = self.doc.xpath(
            u'//li[text()="Available to Spend"]')[0].text_content()\
            .replace(u'Available to Spend', u'').replace(u'Limit', u'').strip()
        paymin = self.amount(u'Payment Due')
        if self.doc.xpath(u'//li[@class="noPaymentDue"]'):
            # If payment date is not scheduled yet, set it somewhere in a
            # distant future, so that we always have a valid date.
            paydate = datetime.now() + timedelta(days=999)
        else:
            rawtext = self.doc.xpath(
                u'//li[contains(text(),"Due Date")]')[0].text_content()
            datetext = re.match('.*(\d\d/\d\d/\d\d\d\d).*', rawtext).group(1)
            paydate = datetime.strptime(datetext, '%m/%d/%Y')
        a = Account()
        a.id = label[-4:]
        a.label = label
        a.currency = Account.get_currency(balance)
        a.balance = -AmTr.decimal_amount(balance)
        a.type = Account.TYPE_CARD
        a.cardlimit = AmTr.decimal_amount(cardlimit)
        a.paymin = AmTr.decimal_amount(paymin)
        if paydate is not None:
            a.paydate = paydate
        return a

    def amount(self, name):
        return u''.join(self.doc.xpath(
            u'//li[text()[.="%s"]]/../li[1]' % name)[0].text_content().split())\
            .replace(u'\xb7', u'.').replace(u'*', u'')


class ActivityPage(SomePage):
    def iter_recent(self):
        records = json.loads(self.doc.xpath(
            '//div[@id="completedActivityRecords"]//input[1]/@value')[0])
        recent = [x for x in records if x['PDF_LOC'] is None]
        for rec in sorted(recent, ActivityPage.cmp_records, reverse=True):
            desc = u' '.join(rec['TRANS_DESC'].split())
            trans = Transaction((rec['REF_NUM'] or u'').strip())
            trans.date = ActivityPage.parse_date(rec['TRANS_DATE'])
            trans.rdate = ActivityPage.parse_date(rec['POST_DATE'])
            trans.type = Transaction.TYPE_UNKNOWN
            trans.raw = desc
            trans.label = desc
            trans.amount = -AmTr.decimal_amount(rec['TRANS_AMOUNT'])
            yield trans

    @staticmethod
    def cmp_records(rec1, rec2):
        return cmp(ActivityPage.parse_date(rec1['TRANS_DATE']),
                   ActivityPage.parse_date(rec2['TRANS_DATE']))

    @staticmethod
    def parse_date(recdate):
        return datetime.strptime(recdate, u'%B %d, %Y')


class StatementsPage(SomePage):
    def iter_statements(self):
        jss = self.doc.xpath(u'//a/@onclick[contains(.,"eBillViewPDFAction")]')
        for js in jss:
            url = re.match("window.open\('([^']*).*\)", js).group(1)
            for i in range(self.browser.MAX_RETRIES):
                try:
                    self.browser.location(url)
                    break
                except ServerError as e:
                    last_error = e
            else:
                raise last_error
            yield self.browser.page


class StatementPage(RawPage):
    LEX = [
        ('charge_amount', r'^\(\$(\d+(,\d{3})*\.\d{2})\) Tj$'),
        ('payment_amount', r'^\(\\\(\$(\d+(,\d{3})*\.\d{2})\\\)\) Tj$'),
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
        return self._tok.simple_read('charge_amount', pos,
                                     lambda xs: -AmTr.decimal_amount(xs[0]))

    def read_payment_amount(self, pos):
        return self._tok.simple_read('payment_amount', pos,
                                     lambda xs: AmTr.decimal_amount(xs[0]))

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
        # TODO: handle PDF encodings properly.
        return (pos+1, unicode(t.value(), errors='ignore')) \
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
