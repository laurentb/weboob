# -*- coding: utf-8 -*-

# Copyright(C) 2012 Romain Bignon
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
from decimal import Decimal
from dateutil.parser import parse as parse_date

from weboob.tools.browser import Page
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.housing import Housing


class SearchResultsPage(Page):
    DATE_RE = re.compile('Annonce \w+ du (.*)')
    MONTHS = {u'janvier':   'january',
              u'février':   'february',
              u'mars':      'march',
              u'avril':     'april',
              u'mai':       'may',
              u'juin':      'june',
              u'juillet':   'july',
              u'août':      'august',
              u'septembre': 'september',
              u'octobre':   'october',
              u'novembre':  'november',
              u'décembre':  'december',
             }

    def iter_housings(self):
        for div in self.document.getroot().cssselect('div.annonce-resume'):
            a = div.cssselect('td.lien-annonce')[0].find('a')
            if a is None:
                # not a real announce.
                continue

            id = a.attrib['href'].split('-')[-1]
            housing = Housing(id)
            housing.title = a.text.strip()
            m = re.match('(\w+) (.+) (\d+)\xa0m\xb2 (.*)', housing.title)
            if m:
                housing.area = Decimal(m.group(3))

            housing.cost = Decimal(div.cssselect('td.prix')[0].text.strip(u' \t\u20ac\xa0€\n\r').replace('.', '').replace(',', '.'))
            housing.currency = u'€'

            m = self.DATE_RE.match(div.cssselect('p.date-publication')[0].text.strip())
            if m:
                date = m.group(1)
                for fr, en in self.MONTHS.iteritems():
                    date = date.replace(fr, en)
                housing.date = parse_date(date)

            metro = div.cssselect('p.metro')
            if len(metro) > 0:
                housing.station = unicode(metro[0].text.strip())
            else:
                housing.station = NotAvailable

            p = div.cssselect('p.annonce-resume-texte')[0]
            b = p.findall('b')
            if len(b) > 0:
                housing.text = b[0].tail.strip()
                housing.location = unicode(b[0].text)
            else:
                housing.text = p.text.strip()

            housing.photos = NotAvailable

            yield housing


class HousingPage(Page):
    def get_housing(self):
        div = self.parser.select(self.document.getroot(), 'div#annonce_detail', 1)
        housing = Housing(self.url.split('-')[-1])

        parts = div.find('h1').text.split(' - ')
        housing.title = parts[0].strip()
        housing.cost = Decimal(parts[1].strip(u' \t\u20ac\xa0€\n\r').replace('.', '').replace(',', '.'))
        housing.currency = u'€'

        m = re.match('(\w+) (.+) (\d+)\xa0m\xb2 (.*)', housing.title)
        if m:
            housing.area = Decimal(m.group(3))

        housing.date = housing.station = housing.location = housing.phone = NotAvailable

        metro = div.cssselect('p.metro')
        if len(metro) > 0:
            housing.station = metro[0].text.strip()

        p = div.cssselect('p.annonce-detail-texte')[0]
        b = p.findall('b')
        if len(b) > 0:
            housing.text = b[0].tail.strip()
            housing.location = unicode(b[0].text)
            if len(b) > 1:
                housing.phone = b[1].text
        else:
            housing.text = p.text.strip()

        housing.details = NotAvailable
        housing.photos = NotAvailable

        return housing
