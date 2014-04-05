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

from weboob.tools.misc import html2text
from weboob.tools.browser import BasePage
import dateutil.parser
import re

from .job import PopolemploiJobAdvert


__all__ = ['SearchPage', 'AdvertPage']


class SearchPage(BasePage):
    def iter_job_adverts(self):
        rows = self.document.getroot().xpath('//table[@class="definition-table ordered"]/tbody/tr')
        for row in rows:
            advert = self.create_job_advert(row)
            if advert:
                yield advert

    def create_job_advert(self, row):
        re_id = re.compile('/candidat/rechercheoffres/resultats\.composantresultatrechercheoffre\.tableauresultatrechercheoffre:detailoffre/(.*?)\?(.*?)', re.DOTALL)
        a = self.parser.select(row, 'td[@headers="offre"]/a', 1, method='xpath')
        if re_id.match(a.attrib['href']):
            _id = u'%s' % (re_id.search(a.attrib['href']).group(1))
            advert = PopolemploiJobAdvert(_id)
            advert.contract_type = u'%s' % self.parser.select(row, 'td[@headers="contrat"]', 1, method='xpath').text
            advert.title = u'%s' % a.text_content().strip()
            society = self.parser.select(row, 'td/div/p/span[@class="company"]', method='xpath')
            if society:
                advert.society_name = society[0].text
            advert.place = u'%s' % self.parser.select(row, 'td[@headers="lieu"]', 1, method='xpath').text_content()
            date = self.parser.select(row, 'td[@headers="dateEmission"]', 1, method='xpath')
            advert.publication_date = dateutil.parser.parse(date.text, dayfirst=True).date()
            return advert


class AdvertPage(BasePage):
    def get_job_advert(self, url, advert):
        content = self.document.getroot().xpath('//div[@id="offre-body"]')[0]
        if not advert:
            _id = self.parser.select(content, 'div/div/ul/li/div[@class="value"]/span', 1, method='xpath').text
            advert = PopolemploiJobAdvert(_id)

        advert.title = u'%s' % self.parser.select(content, 'h4', 1, method='xpath').text.strip()
        advert.job_name = u'%s' % self.parser.select(content, 'h4', 1, method='xpath').text.strip()

        description = self.parser.select(content, 'p[@itemprop="description"]', 1, method='xpath')
        advert.description = html2text(self.parser.tostring(description))

        society_name = self.parser.select(content, 'div[@class="vcard"]/p[@class="title"]/span', method='xpath')

        if society_name:
            advert.society_name = u'%s' % society_name[0].text

        advert.url = url

        place = u'%s' % self.parser.select(content,
                                           'dl/dd/ul/li[@itemprop="addressRegion"]',
                                           1, method='xpath').text
        advert.place = place.strip()

        contract_type = u'%s' % self.parser.select(content,
                                                   'dl/dd/span[@itemprop="employmentType"]',
                                                   1, method='xpath').text

        advert.contract_type = contract_type.strip()

        experience = u'%s' % self.parser.select(content,
                                                'dl/dd/span[@itemprop="experienceRequirements"]',
                                                1, method='xpath').text
        advert.experience = experience.strip()

        formation = u'%s' % self.parser.select(content,
                                               'dl/dd/span[@itemprop="qualifications"]',
                                               1, method='xpath').text
        advert.formation = formation.strip()

        pay = u'%s' % self.parser.select(content,
                                         'dl/dd/span[@itemprop="baseSalary"]',
                                         1, method='xpath').text
        advert.pay = pay.strip()

        return advert
