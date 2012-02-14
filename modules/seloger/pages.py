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


from datetime import date
from dateutil.parser import parse as parse_date

from weboob.tools.browser import BasePage
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.housing import Housing, HousingPhoto


__all__ = ['SearchResultsPage', 'HousingPage']


class SearchResultsPage(BasePage):
    def sanitarize_cost(t):
        return int(float(t.strip(u' \t\u20ac\xa0c€\n\r').replace(u'\xa0', u'').replace(',', '.')))

    def iter_housings(self):
        for div in self.document.getroot().cssselect('div.ann_ann_border'):
            id = div.find('a').attrib['id'][3:]
            housing = Housing(id)

            head = div.cssselect('div.rech_headerann')[0]
            housing.title = head.xpath('.//span[@class="mea1"]/a')[0].text.strip()

            parts = head.xpath('.//span[@class="mea2"]')[0].text.strip().split('+')
            housing.cost = self.sanitarize_cost(parts[0])
            if len(parts) > 1:
                for span in head.xpath('.//span[@class="addprixfr"]/span/strong'):
                    if span.text.strip() == u'Charges\xa0:':
                        housing.cost += self.sanitarize_cost(span.tail)
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
        if housing is None:
            housing = Housing(self.groups[0])

        details = self.document.getroot().xpath('//detailannonce')[0]
        if details.find('titre') is None:
            return None

        housing.title = details.find('titre').text
        housing.text = details.find('descriptif').text.strip()
        housing.cost = int(details.find('prix').text)
        housing.currency = u'€'
        housing.date = parse_date(details.find('dtfraicheur').text)
        housing.area = float(details.find('surface').text)
        housing.phone = details.find('contact').find('telephone').text

        try:
            housing.station = details.find('proximite').text
        except AttributeError:
            housing.station = NotAvailable

        housing.location = details.find('adresse').text
        if not housing.location and details.find('quartier') is not None:
            housing.location = details.find('quartier').text
        if not housing.location:
            housing.location = NotAvailable

        housing.photos = []
        for photo in details.xpath('./photos/photo'):
            if photo.find('bigurl').text:
                url = photo.find('bigurl').text
            else:
                url = photo.find('stdurl').text
            housing.photos.append(HousingPhoto(url))

        housing.details = {}
        for detail in details.xpath('./details/detail'):
            housing.details[detail.find('libelle').text.strip()] = detail.find('valeur').text or 'N/A'

        return housing
