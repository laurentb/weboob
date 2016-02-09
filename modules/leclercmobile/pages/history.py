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

import re
import os
import subprocess
import tempfile
import shutil

from datetime import datetime, date, time
from decimal import Decimal

from weboob.deprecated.browser import Page
from weboob.capabilities.bill import Detail, Bill


def _get_date(detail):
    return detail.datetime


class PdfPage():
    def __init__(self, file):
        self.pdf = file

    def _parse_pdf(self):
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
        txtfile.close()
        os.remove(temptxt)
        return txt

    def get_details(self):
        txt = self._parse_pdf()
        page = txt.split('CONSOMMATION')[2].split('ACTIVITE DETAILLEE')[0]
        lines = page.split('\n')
        lines = [x for x in lines if len(x) > 0]  # Remove empty lines
        details = []
        detail = None
        lines.pop(-1)  # Line to describes pictures
        twolines = False
        for line in lines:
            if "Votre consommation" in line:
                line = line.split(": ", 1)[1]
            if twolines:
                twolines = False
                detail.infos = unicode(line, encoding='utf-8')
            elif re.match('[A-Za-z]', line[0]):
                # We have a new element, return the other one
                if detail is not None:
                    details.append(detail)
                detail = Detail()
                split = re.split("(\d)", line, maxsplit=1)
                detail.price = Decimal(0)
                if len(split) > 2:
                    detail.infos = unicode(split[1] + split[2], encoding='utf-8')
                else:
                    twolines = True
                if '€' in line:
                    specialprice = split[1] + split[2]
                    detail.price = Decimal(specialprice.replace('€', ''))
                detail.label = unicode(split[0], encoding='utf-8')
            elif '€' in line:
                detail.price = Decimal(line.replace('€', ''))
            else:
                detail.infos = unicode(line, encoding='utf-8')
        details.append(detail)
        return details

    # Standard pdf text extractor take text line by line
    # But the position in the file is not always the "real" position to display...
    # It produce some unsorted and unparsable data
    # Example of bad software: pdfminer and others python tools
    # This is why we have to use "ebook-convert" from calibre software,
    # it is the only one to 'reflow" text and give some relevant results
    # The bad new is that ebook-convert doesn't support simple use with stdin/stdout
    def get_calls(self):
        txt = self._parse_pdf()
        pages = txt.split("DEBIT")
        pages.pop(0)  # remove headers
        details = []
        for page in pages:
            page = page.split('RÉGLO MOBILE')[0].split('N.B. Prévoir')[0]  # remove footers
            lines = page.split('\n')
            lines = [x for x in lines if len(x) > 0]  # Remove empty lines
            numitems = (len(lines) + 1) / 4  # Each line has five columns
            lines.pop(0)  # remove the extra € symbol
            modif = 0
            i = 0
            while i < numitems:
                if modif != 0:
                    numitems = ((len(lines) + 1 + modif) / 4)
                base = i * 4 - modif
                dateop = base
                corres = base + 1
                duree = base + 2
                price = base + 3
                if "Changement vers le Forfait" in lines[base]:
                    modif += 1
                    i += 1
                    continue
                # Special case with 5 columns, the operation date is not in the first one
                if len(re.split("(\d+\/\d+\/\d+)", lines[dateop])) < 2:
                    lines[base + 1] = lines[base] + " " + lines[base + 1]
                    dateop = base + 1
                    corres = base + 2
                    duree = base + 3
                    price = base + 4
                    modif -= 1
                detail = Detail()
                splits = re.split("(\d+\/\d+\/\d+)", lines[dateop])
                mydate = date(*reversed([int(x) for x in splits[1].split("/")]))
                mytime = time(*[int(x) for x in splits[2].split(":")])
                detail.datetime = datetime.combine(mydate, mytime)
                if lines[corres] == '-':
                    lines[corres] = ""
                if lines[duree] == '-':
                    lines[duree] = ''
                detail.label = unicode(splits[0], encoding='utf-8', errors='replace') + u" " + lines[corres] + u" " + lines[duree]
                # Special case with only 3 columns, we insert a price
                if "Activation de votre ligne" in detail.label or u"Résiliation" in detail.label:
                    lines.insert(price, '0')
                try:
                    detail.price = Decimal(lines[price].replace(',', '.'))
                except:
                    # In some special cases, there are no price column. Try to detect it
                    if "Inclus" not in lines[price]:
                        modif += 1
                    detail.price = Decimal(0)

                details.append(detail)
                i += 1
        return sorted(details, key=_get_date, reverse=True)


class HistoryPage(Page):
    def on_loaded(self):
        pass

    def getmaxid(self):
        max = 1
        while len(self.document.xpath('//li[@id="liMois%s"]' % max)) > 0:
            max += 1
        return max - 1

    def date_bills(self, parentid):
        max = 1
        while len(self.document.xpath('//li[@id="liMois%s"]' % max)) > 0:
            li = self.document.xpath('//li[@id="liMois%s"]' % max)[0]
            max += 1
            link = li.xpath('a')[0]
            bill = Bill()
            bill._url = link.attrib['href']
            bill.label = unicode(link.text)
            bill.format = u"pdf"
            bill.type = u"bill"
            bill.id = parentid + bill.label.replace(' ', '')
            yield bill
