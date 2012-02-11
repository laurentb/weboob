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
from datetime import date

from weboob.tools.browser import BasePage, BrokenPageError
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.housing import Housing


__all__ = ['SearchResultsPage', 'HousingPage']


def sanitarize_cost(t):
    return int(float(t.strip(u' \t\u20ac\xa0c€\n\r').replace(u'\xa0', u'').replace(',', '.')))

class SearchResultsPage(BasePage):
    def iter_housings(self):
        for div in self.document.getroot().cssselect('div.ann_ann_border'):
            id = div.find('a').attrib['id'][3:]
            housing = Housing(id)

            head = div.cssselect('div.rech_headerann')[0]
            housing.title = head.xpath('.//span[@class="mea1"]/a')[0].text.strip()

            parts = head.xpath('.//span[@class="mea2"]')[0].text.strip().split('+')
            housing.cost = sanitarize_cost(parts[0])
            if len(parts) > 1:
                for span in head.xpath('.//span[@class="addprixfr"]/span/strong'):
                    if span.text.strip() == u'Charges\xa0:':
                        housing.cost += sanitarize_cost(span.tail)
            housing.currency = u'€'

            sub = div.xpath('.//div[@class="rech_desc_right_photo"]')[0]
            span = sub.xpath('./span[@class="mea7"]')
            if len(span) > 0:
                housing.text = '%s - %s' % (span[0].text.strip(), span[0].tail.strip())
            else:
                housing.text = div.xpath('.//div[@class="rech_ville"]')[0].tail.strip()
            housing.text = housing.text.replace('\r\n', ' ')
            housing.location = sub.xpath('.//div[@class="rech_ville"]/strong')[0].text.strip()

            housing.date = date(*map(int, reversed(sub.xpath('.//div[@class="rech_majref"]/strong')[0].tail.strip('- \xa0\r\t\n').split('/'))))
            yield housing

class HousingPage(BasePage):
    def get_housing(self, housing=None):
        doc = self.document.getroot()
        if housing is None:
            housing = Housing(self.url.split('/')[-1].rstrip('.htm'))

        housing.title = doc.xpath('//head/title')[0].text
        housing.text = doc.xpath('//head/meta[@name="description"]')[0].attrib['content']
        txt = doc.xpath('//meta[@itemprop="price"]')[0].attrib['content'].strip()
        m = re.match(u'(\d+)\xa0\u20ac(\+ch|cc)(Charges: (\d+)\u20ac)?', txt)
        if not m:
            raise BrokenPageError('Unable to parse price %r' % txt)

        housing.cost = sanitarize_cost(m.group(1))
        if m.group(4):
            housing.cost += sanitarize_cost(m.group(4))
        housing.currency = u'€'

        housing.date = date(*map(int, reversed(doc.xpath('//span[@class="maj"]/b')[0].text.split(' / '))))
        housing.area = int(doc.xpath('//li[@title="Surface"]/b')[0].text.strip(u'\xa0m\xb2'))

        try:
            housing.station = doc.xpath('//dd[@class="metro_paris"]')[0].text.strip()
        except IndexError:
            housing.station = NotAvailable

        try:
            housing.phone = doc.xpath('//div[@class="tel"]')[0].text.strip()
        except IndexError:
            housing.phone = NotAvailable

        try:
            housing.location = doc.xpath('//div[@class="adresse"]/b')[0].tail.strip().replace('\r\n', ' ')
        except IndexError:
            housing.location = NotAvailable

        return housing
