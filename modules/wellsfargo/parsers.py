# -*- coding: utf-8 -*-

# Copyright(C) 2014      Oleg Plakhotniuk
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

from weboob.capabilities.bank import Transaction
from weboob.tools.capabilities.bank.transactions import AmericanTransaction
from decimal import Decimal
from tempfile import mkstemp
import subprocess
import os
import re
import datetime


def clean_amount(text):
    return Decimal(AmericanTransaction.clean_amount(text))


def clean_label(text):
    """
    Web view and statements use different label formatting.
    User shouldn't be able to see the difference, so we
    need to make labels from both sources look the same.
    """
    return re.sub(u' +', u' ', text.strip().upper(), re.UNICODE)


def full_date(date, date_from, date_to):
    """
    Makes sure that date is close to the given range.
    Transactions dates in a statement contain only day and month.
    Statement dates range have a year though.
    Merge them all together to get a full transaction date.
    """
    dates = [datetime.datetime(d.year, date.month, date.day)
             for d in (date_from, date_to)]

    # Ideally, pick the date within given range.
    for d in dates:
        if date_from <= d <= date_to:
            return d

    # Otherwise, return the most recent date in the past
    return min(dates, key=lambda d: abs(d-date_from))


def decompress_pdf(inpdf):
    inh, inname = mkstemp(suffix='.pdf')
    outh, outname = mkstemp(suffix='.pdf')
    os.write(inh, inpdf)
    os.close(inh)
    os.close(outh)

    # mutool is a part of MuPDF (http://www.mupdf.com).
    subprocess.call(['mutool', 'clean', '-d', inname, outname])

    with open(outname) as f:
        outpdf = f.read()
    os.remove(inname)
    os.remove(outname)
    return outpdf


class StatementParser(object):
    """
    Each "read_*" method which takes position as its argument,
    returns next token position if read was successful,
    and the same position if it was not.
    """
    def __init__(self, pdf):
        self._pdf = decompress_pdf(pdf)
        self._tok = StatementTokenizer(self._pdf)

    def read_card_transactions(self):
        # Early check if this is a card account statement at all.
        if '[(Transactions)] TJ' not in self._pdf:
            return

        # Read statement dates range.
        date_from, date_to = self.read_first_date_range()

        # Read transactions.
        pos = 0
        while not self._tok.tok(pos).is_eof():
            pos, trans = self.read_card_transaction(pos, date_from, date_to)
            if trans:
                yield trans
            else:
                pos += 1

    def read_cash_transactions(self):
        # Early check if this is a cash account statement at all.
        if '[(Transaction history)] TJ' not in self._pdf:
            return

        # Read statement dates range.
        date_from, date_to = self.read_first_date_range()

        # Read transactions.
        pos = 0
        while not self._tok.tok(pos).is_eof():
            pos, trans = self.read_cash_transaction(pos, date_from, date_to)
            if trans:
                yield trans
            else:
                pos += 1

    def read_first_date_range(self):
        pos = 0
        while not self._tok.tok(pos).is_eof():
            pos, date_range = self.read_date_range(pos)
            if date_range is not None:
                return date_range
            else:
                pos += 1

    def read_card_transaction(self, pos, date_from, date_to):
        INDENT_CHARGES = 520

        startPos = pos

        pos, tdate = self.read_date(pos)
        pos, pdate_layout = self.read_layout_tm(pos)
        pos, pdate = self.read_date(pos)
        pos, ref_layout = self.read_layout_tm(pos)
        pos, ref = self.read_ref(pos)
        pos, desc = self.read_multiline_desc(pos)
        pos, amount = self.read_indent_amount(
            pos,
            range_minus = (INDENT_CHARGES, 9999),
            range_plus = (0, INDENT_CHARGES))

        if tdate is None or pdate_layout is None or pdate is None \
        or ref_layout is None or ref is None or desc is None or amount is None:
            return startPos, None
        else:
            tdate = full_date(tdate, date_from, date_to)
            pdate = full_date(pdate, date_from, date_to)

            trans = Transaction(ref)
            trans.date = tdate
            trans.rdate = pdate
            trans.type = Transaction.TYPE_UNKNOWN
            trans.raw = desc
            trans.label = desc
            trans.amount = amount
            return pos, trans

    def read_cash_transaction(self, pos, date_from, date_to):
        INDENT_BALANCE = 520
        INDENT_WITHDRAWAL = 470

        startPos = pos

        pos, date = self.read_date(pos)
        pos, _ = self.read_star(pos)
        pos, desc = self.read_multiline_desc(pos)
        pos, amount = self.read_indent_amount(
            pos,
            range_plus = (0, INDENT_WITHDRAWAL),
            range_minus = (INDENT_WITHDRAWAL, INDENT_BALANCE),
            range_skip = (INDENT_BALANCE, 9999))

        if desc is None or date is None or amount is None:
            return startPos, None
        else:
            date = full_date(date, date_from, date_to)

            trans = Transaction(u'')
            trans.date = date
            trans.rdate = date
            trans.type = Transaction.TYPE_UNKNOWN
            trans.raw = desc
            trans.label = desc
            trans.amount = amount
            return pos, trans

    def read_multiline_desc(self, pos):
        startPos = pos

        descs = []
        while True:
            prevPos = pos
            pos, layout = self.read_layout_tm(pos)
            pos, desc = self.read_text(pos)
            if layout is None or desc is None:
                pos = prevPos
                break
            else:
                descs.append(desc)

        if descs:
            return pos, clean_label(' '.join(descs))
        else:
            return startPos, None

    def read_indent_amount(self, pos, range_skip=(0,0), range_plus=(0,0),
                           range_minus=(0,0)):
        startPos = pos

        # Read layout-amount pairs.
        amounts = []
        while True:
            prevPos = pos
            pos, layout = self.read_layout_tm(pos)
            pos, amount = self.read_amount(pos)
            if layout is None or amount is None:
                pos = prevPos
                break
            else:
                amounts.append((layout, amount))

        if not amounts:
            return startPos, None
        else:
            # Infer amount type by its indentation in the layout.
            amount_total = clean_amount('0')
            for (_, _, _, _, indent, _), amount in amounts:
                within = lambda xmin_xmax: xmin_xmax[0] <= indent <= xmin_xmax[1]
                if within(range_skip):
                    continue
                elif within(range_plus):
                    amount_total += amount
                elif within(range_minus):
                    amount_total -= amount
            return pos, amount_total

    def read_star(self, pos):
        pos1, star1 = self.read_star_1(pos)
        pos2, star2 = self.read_star_2(pos)
        if star1 is not None:
            return pos1, star1
        else:
            return pos2, star2

    def read_star_1(self, pos):
        startPos = pos

        vals = list()
        pos, v = self.read_layout_tz(pos); vals.append(v)
        pos, v = self.read_layout_tc(pos); vals.append(v)
        pos, v = self.read_layout_tw(pos); vals.append(v)
        pos, v = self.read_layout_tf(pos); vals.append(v)
        pos, v = self.read_layout_tm(pos); vals.append(v)
        pos, star = self.read_text(pos)
        pos, v = self.read_layout_tz(pos); vals.append(v)
        pos, v = self.read_layout_tc(pos); vals.append(v)
        pos, v = self.read_layout_tw(pos); vals.append(v)
        pos, v = self.read_layout_tf(pos); vals.append(v)

        if star == 'S' and None not in vals:
            return pos, star
        else:
            return startPos, None

    def read_star_2(self, pos):
        startPos = pos

        vals = list()
        pos, v = self.read_layout_tf(pos); vals.append(v)
        pos, v = self.read_layout_tm(pos); vals.append(v)
        pos, star = self.read_text(pos)
        pos, v = self.read_layout_tf(pos); vals.append(v)

        if star == 'S' and None not in vals:
            return pos, star
        else:
            return startPos, None

    def read_date(self, pos):
        t = self._tok.tok(pos)
        return (pos+1, datetime.datetime.strptime(t.value(), '%m/%d')) \
            if t.is_date() else (pos, None)

    def read_text(self, pos):
        t = self._tok.tok(pos)
        #TODO: handle PDF encodings properly.
        return (pos+1, unicode(t.value(), errors='ignore')) \
            if t.is_text() else (pos, None)

    def read_amount(self, pos):
        t = self._tok.tok(pos)
        return (pos+1, clean_amount(t.value())) \
            if t.is_amount() else (pos, None)

    def read_date_range(self, pos):
        t = self._tok.tok(pos)
        if t.is_date_range_1():
            return (pos+1, [datetime.datetime.strptime(v, '%B %d, %Y')
                            for v in t.value()])
        elif t.is_date_range_2():
            return (pos+1, [datetime.datetime.strptime(v, '%m/%d/%Y')
                            for v in t.value()])
        else:
            return (pos, None)

    def read_ref(self, pos):
        t = self._tok.tok(pos)
        return (pos+1, t.value()) if t.is_ref() else (pos, None)

    def read_layout_tz(self, pos):
        t = self._tok.tok(pos)
        return (pos+1, t.value()) if t.is_layout_tz() else (pos, None)

    def read_layout_tc(self, pos):
        t = self._tok.tok(pos)
        return (pos+1, t.value()) if t.is_layout_tc() else (pos, None)

    def read_layout_tw(self, pos):
        t = self._tok.tok(pos)
        return (pos+1, t.value()) if t.is_layout_tw() else (pos, None)

    def read_layout_tf(self, pos):
        t = self._tok.tok(pos)
        return (pos+1, t.value()) if t.is_layout_tf() else (pos, None)

    def read_layout_tm(self, pos):
        t = self._tok.tok(pos)
        return (pos+1, [float(v) for v in t.value()]) \
            if t.is_layout_tm() else (pos, None)


class StatementTokenizer(object):
    def __init__(self, pdf):
        self._tok = [StatementToken(line) for line in pdf.split('\n')]

    def tok(self, index):
        if 0 <= index < len(self._tok):
            return self._tok[index]
        else:
            return StatementToken(eof=True)


class StatementToken(object):
    """
    Simple regex-based lexer.
    There's a lexing table consisting of type-regex tuples.
    Text line is sequentially matched against regexes and first
    successful match defines the type of the token.
    """
    LEX = [
        ('amount', r'^\[\(([0-9,]+\.\d+)\)\] TJ$'),
        ('date', r'^\[\((\d+/\d+)\)\] TJ$'),
        ('date_range_1', r'^\[\(([A-z]+ \d+, \d{4})'
                          r' - ([A-z]+ \d+, \d{4})\)\] TJ$'),
        ('date_range_2', r'^\[\((\d{2}/\d{2}/\d{4})'
                         r' to (\d{2}/\d{2}/\d{4})\)\] TJ$'),
        ('layout_tz', r'^(\d+\.\d{2}) Tz$'),
        ('layout_tc', r'^(\d+\.\d{2}) Tc$'),
        ('layout_tw', r'^(\d+\.\d{2}) Tw$'),
        ('layout_tf', r'^/F(\d) (\d+\.\d{2}) Tf$'),
        ('layout_tm', r'^' + (r'(\d+\.\d+ )'*6) + r'Tm$'),
        ('ref', r'^\[\(([0-9A-Z]{17})\)\] TJ$'),

        ('text', r'^\[\(([^\)]+)\)\] TJ$')
    ]

    def __init__(self, line=None, eof=False):
        self._eof = eof
        self._value = None
        self._type = None
        if line is not None:
            for type_, regex in self.LEX:
                m = re.match(regex, line, flags=re.UNICODE)
                if m:
                    self._type = type_
                    if len(m.groups()) == 1:
                        self._value = m.groups()[0]
                    elif m.groups():
                        self._value = m.groups()
                    else:
                        self._value = m.group(0)
                    break

    def is_eof(self):
        return self._eof

    def value(self):
        return self._value

for type_, _ in StatementToken.LEX:
    setattr(StatementToken, 'is_%s' % type_,
        eval('lambda self: self._type == "%s"' % type_))

