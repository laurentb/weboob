# -*- coding: utf-8 -*-

# Copyright(C) 2014      Oleg Plakhotniuk
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import datetime
import re

from weboob.capabilities.bank import Transaction
from weboob.tools.capabilities.bank.transactions import AmericanTransaction as AmTr
from weboob.tools.compat import unicode
from weboob.tools.date import closest_date
from weboob.tools.pdf import decompress_pdf
from weboob.tools.tokenizer import ReTokenizer


def clean_label(text):
    """
    Web view and statements use different label formatting.
    User shouldn't be able to see the difference, so we
    need to make labels from both sources look the same.
    """
    for pattern in [r' \d+\.\d+ +POUND STERLING',
                    'Subject to Foreign Fee',
                    'Description']:
        text = re.sub(pattern, '', text, re.UNICODE)
    return re.sub(r' +', ' ', text.strip().upper(), re.UNICODE)


def formatted(read_func):
    """
    Reads boilerplate PDF formatting around the data of interest.
    """
    def wrapped(self, pos):
        startPos = pos
        pos, ws = self.read_whitespace(pos)
        pos, bt = self.read_layout_bt(pos)
        pos, tf = self.read_layout_tf(pos)
        pos, tm = self.read_layout_tm(pos)
        pos, data = read_func(self, pos)
        pos, et = self.read_layout_et(pos)
        if ws is None or bt is None or tf is None \
           or tm is None or data is None or et is None:
            return startPos, None
        else:
            return pos, data
    return wrapped


class StatementParser(object):
    """
    Each "read_*" method takes position as its argument,
    and returns next token position if read was successful,
    or the same position if it was not.
    """

    LEX = [
        ('date_range', r'^\((\d{2}/\d{2}/\d{2})-(\d{2}/\d{2}/\d{2})\) Tj$'),
        ('amount', r'^\((-?\$\d+(,\d{3})*\.\d{2})\) Tj$'),
        ('date', r'^\((\d{2}/\d{2})\) Tj$'),
        ('text', r'^\((.*)\) Tj$'),
        ('layout_tf', r'^.* Tf$'),
        ('layout_tm', r'^' + (6*r'([^ ]+) ') + r'Tm$'),
        ('layout_bt', r'^BT$'),
        ('layout_et', r'^ET$'),
        ('whitespace', r'^$')
    ]

    def __init__(self, pdf):
        self._pdf = decompress_pdf(pdf)
        self._tok = ReTokenizer(self._pdf, '\n', self.LEX)

    def read_transactions(self):
        # Read statement dates range.
        date_from, date_to = self.read_first_date_range()

        # Read transactions.
        pos = 0
        while not self._tok.tok(pos).is_eof():
            pos, trans = self.read_transaction(pos, date_from, date_to)
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

    def read_date_range(self, pos):
        t = self._tok.tok(pos)
        if t.is_date_range():
            return (pos+1, [datetime.datetime.strptime(v, '%m/%d/%y')
                            for v in t.value()])
        else:
            return (pos, None)

    def read_transaction(self, pos, date_from, date_to):
        startPos = pos

        pos, tdate = self.read_date(pos)
        pos, pdate = self.read_date(pos)

        # Early check to call read_multiline_desc() only when needed.
        if tdate is None:
            return startPos, None

        pos, desc = self.read_multiline_desc(pos)
        pos, amount = self.read_amount(pos)

        if desc is None or amount is None:
            return startPos, None
        else:
            # Sometimes one date is missing.
            pdate = pdate or tdate

            tdate = closest_date(tdate, date_from, date_to)
            pdate = closest_date(pdate, date_from, date_to)

            trans = Transaction()
            trans.date = tdate
            trans.rdate = pdate
            trans.type = Transaction.TYPE_UNKNOWN
            trans.raw = desc
            trans.label = desc
            trans.amount = -amount
            return pos, trans

    def read_multiline_desc(self, pos):
        """
        Read transaction description which can span over multiple lines.
        Amount must always follow the multiline description.
        But multiline description might be split by page break.
        After reading first line of the description, we skip everything
        which is not an amount and which has different horizontal offset
        than the first read line.
        """
        startPos = pos

        descs = []
        xofs = None
        while not self._tok.tok(pos).is_eof():
            pos, desc_tm = self.read_text(pos)
            if desc_tm is None:
                if not descs:
                    break
                prev_pos = pos
                pos, amount = self.read_amount(pos)
                if amount is not None:
                    pos = prev_pos
                    break
                pos += 1
            else:
                desc, tm = desc_tm
                if xofs is None:
                    _, _, _, _, xofs, _ = tm
                _, _, _, _, xofs_new, _ = tm
                if xofs == xofs_new:
                    descs.append(desc)
                else:
                    pos += 1

        if descs:
            return pos, clean_label(' '.join(descs))
        else:
            return startPos, None

    def __getattr__(self, name):
        if name.startswith('read_'):
            return lambda pos: self._tok.simple_read(name[5:], pos)
        raise AttributeError()

    @formatted
    def read_date(self, pos):
        def parse_date(v):
            for year in [1900, 1904]:  # try leap and non-leap years
                fullstr = '%s/%i' % (v, year)
                try:
                    return datetime.datetime.strptime(fullstr, '%m/%d/%Y')
                except ValueError as e:
                    last_error = e
            raise last_error

        return self._tok.simple_read('date', pos, parse_date)

    @formatted
    def read_amount(self, pos):
        return self._tok.simple_read('amount', pos,
                                     lambda xs: AmTr.decimal_amount(xs[0]))

    def read_text(self, pos):
        startPos = pos
        pos, ws = self.read_whitespace(pos)
        pos, bt = self.read_layout_bt(pos)
        pos, tf = self.read_layout_tf(pos)
        pos, tm = self.read_layout_tm(pos)
        pos, text = self._tok.simple_read('text', pos,
            lambda v: unicode(v, errors='ignore'))
        pos, et = self.read_layout_et(pos)
        if ws is None or bt is None or tf is None \
           or tm is None or text is None or et is None:
            return startPos, None
        else:
            return pos, (text, tm)
