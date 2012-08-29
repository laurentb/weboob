# -*- coding: utf-8 -*-

# Copyright(C) 2012 Florent Fourcot
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


import subprocess
import tempfile
import shutil

from datetime import datetime, date, time
from decimal import Decimal

from weboob.tools.browser import BasePage
from weboob.capabilities.bill import Detail


__all__ = ['HistoryPage', 'PdfPage']


def _get_date(detail):
    return detail.datetime


class PdfPage():
    def __init__(self, file):
        self.pdf = file

    # Standard pdf text extractor take text line by line
    # But the position in the file is not always the "real" position to display...
    # It produce some unsorted and unparsable data
    # Example of bad software: pdfminer and others python tools
    # This is why we have to use "ebook-convert" from calibre software,
    # it is the only one to 'reflow" text and give some relevant results
    # The bad new is that ebook-convert doesn't support simple use with stdin/stdout
    def get_calls(self):
        pdffile = tempfile.NamedTemporaryFile(bufsize=100000, mode='w', suffix='.pdf')
        temptxt = pdffile.name.replace('.pdf', '.txt')
        cmd = "ebook-convert"
        stdout = open("/dev/null", "w")
        shutil.copyfileobj(self.pdf, pdffile)
        pdffile.flush()
        subprocess.call([cmd, pdffile.name, temptxt], stdout=stdout)
        pdffile.close()
        txtfile = open(temptxt, 'r')
        txt = txtfile.read()
        pages = txt.split("DEBIT (€)")
        pages.pop(0)  # remove headers
        details = []
        for page in pages:
            page = page.split('RÉGLO MOBILE')[0].split('N.B. Prévoir')[0]  # remove footers
            lines = page.split('\n')
            lines = [x for x in lines if len(x) > 0]  # Remove empty lines
            numitems = (len(lines) + 1) / 5  # Each line has five columns
            for i in range(numitems):
                nature = i * 5
                dateop = nature + 1
                corres = dateop + 1
                duree = corres + 1
                price = duree + 1

                detail = Detail()
                mydate = date(*reversed([int(x) for x in lines[dateop].split(' ')[0].split("/")]))
                mytime = time(*[int(x) for x in lines[dateop].split(' ')[1].split(":")])
                detail.datetime = datetime.combine(mydate, mytime)
                if lines[corres] == '-':
                    lines[corres] = ""
                if lines[duree] == '-':
                    lines[duree] = ''
                detail.label = unicode(lines[nature], encoding='utf-8', errors='replace') + u" " + lines[corres] + u" " + lines[duree]
                # Special case with only 4 columns, we insert a price
                if "Activation de votre ligne" in detail.label:
                    lines.insert(price, '0')
                try:
                    detail.price = Decimal(lines[price].replace(',', '.'))
                except:
                    detail.price = Decimal(0)

                details.append(detail)
        return sorted(details, key=_get_date, reverse=True)


class HistoryPage(BasePage):
    def on_loaded(self):
        pass

    def getmaxid(self):
        max = 1
        while len(self.document.xpath('//li[@id="liMois%s"]' % max)) > 0:
            max += 1
        return max - 1
