# -*- coding: utf-8 -*-

# Copyright(C) 2013 Mathieu Jourdan
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

from datetime import date
from decimal import Decimal

from weboob.deprecated.browser import Page
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.bill import Detail, Bill


class HistoryPage(Page):

    def on_loaded(self):
        self.details = []
        self.bills = []

        # Latest bill
        div = self.document.xpath('//div[@class="consulter_dernierefacture"]')[0]
        bdate = div.xpath('p[@class="date"]/span[@class="textetertiaire"]')[0].text
        bprice = div.xpath('p[@class="montant"]/span[@class="textetertiaire"]')[0].text
        link = div.xpath('a[@id="display_popin"]')[0].attrib['href']
        mydate = date(*reversed([int(x) for x in bdate.split("/")]))
        price = Decimal(bprice.strip(u' € TTC').replace(',', '.'))
        self.bills.append(self._create_bill(mydate, price, link))

        # Previous bills
        table = self.document.xpath('//table[@class="afficher_factures"]')[0]
        for tr in table[0].xpath('//tbody/tr'):
            cells = tr.xpath('td')
            bdate = unicode(cells[0].text.strip())
            mydate = date(*reversed([int(x) for x in bdate.split("/")]))
            bprice = unicode(cells[1].text)
            price = Decimal(bprice.strip(u' €').replace(',', '.'))
            link = cells[3].xpath('a')[0].attrib['href']
            self.bills.append(self._create_bill(mydate, price, link))

    def _create_bill(self, date, price, link):
        bill = Bill()
        bill.id = date.__str__().replace('-', '')
        bill.date = date
        bill._price = price
        bill._url = link
        bill.format = u'pdf'
        bill.type = u'bill'
        bill.label = unicode(price)
        return bill

    def get_details(self):
        return self.details

    def get_documents(self):
        return self.bills


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

    def _parse_page(self, page):

        # Regexp
        footnote = re.compile(r'\([0-9]\) ')                # (f)
        ht = re.compile('HT par mois')
        base = re.compile('la base de')
        enddate = re.compile('\d\d\/\d\d\/\d\d')            # YY/MM/DD
        endwithdigit = re.compile('\d+$')                   # blah blah 42
        textwithcoma = re.compile('([a-z]|\d{4})\,')        # blah 2012, blah blah

        # Parsing
        details = []
        for title in ['Abonnement',
                      'Consommation',
                      'Contributions et taxes liées à l\'énergie']:
            section = page.split(title, 1)[1].split('Total ')[0]

            # When a line holds '(0)', a newline is missing.
            section = re.sub(footnote, '\n', section)

            lines = section.split('\n')
            lines = [x for x in lines if len(x) > 0]  # Remove empty lines
            detail = None

            for line in lines:
                if re.match('[A-Za-z]', line[0]):

                    # Things we want to merge with the one just before
                    if 'facturées' in line:
                        # Long lines are sometimes split, so we try to join them
                        # That is the case for:
                        # 'Déduction du montant des consommations
                        # estimées facturées du 00/00/00 au 00/00/00'
                        detail.label = detail.label + u' ' + unicode(line, encoding='utf-8')

                    # Things for which we want a new detail
                    else:
                        # Entering here, we will instantiate a new detail.
                        # We hadn't so before because of fragmented lines.
                        if detail is not None and detail.label is not NotAvailable:
                            # We have a new element, return the other one
                            details.append(detail)
                        detail = Detail()
                        detail.price = Decimal(0)

                        # If the coma is not a decimal separator, then
                        # this is is probably a loooong sentence.
                        # When it comes to jokes, keep it short and sweet.
                        line = re.split(textwithcoma, line)[0]

                        # Things we want for sure
                        if re.findall(enddate, line):
                            # When a line has been badly split after a date,
                            # We want the label to end after the date, and maybe
                            # the second part to be the info
                            mydate = re.search(enddate, line).group(0)
                            mylist = line.rpartition(mydate)
                            label = mylist[0] + mylist[1]
                            detail.label = unicode(label, encoding='utf-8')
                        elif re.findall(endwithdigit, line):
                            # What is this stupid number at the end of the line?
                            # Line should have been split before the number
                            detail.label = unicode(re.split(endwithdigit, line)[0], encoding='utf-8')
                        # Things we don't want for sure
                        elif ')' in line and '(' not in line:
                            # First part of the parenthesis should have been drop before
                            # Avoid to create a new empty detail
                            detail.label = NotAvailable
                        elif re.match(base, line):
                            # This string should come always after a date,
                            # usually, it will match one of the cases above.
                            # Sometimes, it appears on a new line we don't need.
                            detail.label = NotAvailable
                        elif re.match(ht, line):
                            # '00,00 € HT par mois' may have been split after HT
                            # We don't need of the second line
                            detail.label = NotAvailable
                        # Things we probably want to keep
                        else:
                            # Well, maybe our line is correct, after all.
                            # Not much to do.
                            detail.label = unicode(line, encoding='utf-8')
                        detail.infos = NotAvailable
                elif ' %' in line:
                    if isinstance(detail, Detail):
                        # Sometimes the vat is not on a new line:
                        # '00,00 00,0 %' instead of '00,0 %'
                        vat = line.split()[line.count(' ')-1].replace(',', '.')
                        detail.infos = unicode('TVA: ' + vat)
                elif ' €' in line:
                    price = line.replace(',', '.')
                    if isinstance(detail, Detail):
                        detail.price = Decimal(price.strip(' €'))
                elif re.match(enddate, line):
                    # Line holding dates may have been mixed up
                    label = detail.label.split(' au ')[0] + u' au ' + unicode(line, encoding='utf-8')
                    detail.label = label
            if detail.label is not NotAvailable:
                # Do not append empty details to the list
                # It seemed easier to create details anyway than dealing
                # with None objects
                details.append(detail)
        return details

    def get_details(self, label):
        txt = self._parse_pdf()
        page = None
        if label == u'Gaz naturel':
            page = txt.split('GAZ NATUREL')[1].split('TOTAL GAZ NATUREL TTC')[0]
        elif label == u'Electricité':
            page = txt.split('ELECTRICITE')[1].split('TOTAL ELECTRICITE TTC')[0]
        else:
            pass
        return self._parse_page(page)
