# -*- coding: utf-8 -*-

# Copyright(C) 2013      Bezleputh
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


from weboob.deprecated.browser import Page
import dateutil.parser
import re

from .job import LolixJobAdvert


class AdvertPage(Page):
    def get_job_advert(self, url, advert):
        tables = self.document.getroot().xpath('//td[@class="Contenu"]/table')
        rows = self.parser.select(tables[2], 'tr')

        if not advert:
            advert = LolixJobAdvert(self.group_dict['id'])

        advert.url = url
        advert.society_name = u'%s' % self.parser.select(tables[3], 'tr/td/a', 1, method='xpath').text
        return self.fill_job_advert(rows, advert)

    def fill_job_advert(self, rows, advert):
        advert.title = u'%s' % self.parser.select(rows[0], 'td', 1).text_content()
        isDescription = False
        for row in rows:
            cols = self.parser.select(row, 'td')
            if isDescription:
                advert.description = u'%s' % cols[0].text_content()
                isDescription = False

            elif cols[0].text == u'Poste :':
                advert.job_name = u'%s' % cols[1].text_content()

            elif cols[0].text == u'Contrat :':
                advert.contract_type = u'%s' % cols[1].text_content()

            elif cols[0].text and cols[0].text.find(u'Rémunération :') != -1:
                advert.pay = u'%s' % cols[1].text_content()

            elif cols[0].text and cols[0].text.find(u'Région :') != -1:
                advert.place = u'%s' % cols[1].text_content()

            elif cols[0].text == u'Détails :':
                isDescription = True

            #else:
            #    print cols[0].text
        return advert


class SearchPage(Page):
    def iter_job_adverts(self, pattern):
        rows = self.document.getroot().xpath('//td[@class="Contenu"]/table/tr')
        for row in rows:
            cols = self.is_row_advert(row)
            if cols is not None:
                advert = self.create_job_advert(cols)
                if pattern:
                    if pattern in advert.title:
                        yield advert
                else:
                    yield advert

    def is_row_advert(self, row):
        cols = self.parser.select(row, 'td')
        if len(cols) > 1:
            d = dict(cols[1].attrib)
            if 'class' in d.keys():
                if 'ListeDark' == d['class'] or 'ListeLight' == d['class']:
                    return cols

    def create_job_advert(self, cols):
        a = self.parser.select(cols[2], 'a')[0]
        advert = LolixJobAdvert(re.match(r'offre.php\?id=(.*)', a.attrib['href']).group(1))
        advert.publication_date = dateutil.parser.parse(cols[0].text).date()
        advert.society_name = u'%s' % self.parser.select(cols[1], 'a')[0].text
        advert.title = u'%s' % a.text
        return advert
