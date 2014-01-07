# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
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
from .job import RegionsJobAdvert
from datetime import datetime, date
import re

__all__ = ['SearchPage']


class SearchPage(BasePage):
    def iter_job_adverts(self, website):
        re_id = re.compile('(.*?)numoffre=(.*?)&de=consultation', re.DOTALL)
        lis = self.document.getroot().xpath('//div[@id="liste_offres"]/ul/li')
        for li in lis:
            a = self.parser.select(li, 'div/span[@class="offres_poste"]/a', 1, method='xpath')
            _id = u'%s|%s' % (website, re_id.search(a.attrib['href']).group(2))
            advert = RegionsJobAdvert(_id)
            advert.title = u'%s' % a.text
            advert.society_name = u'%s' % self.parser.select(li, 'div/span[@class="offres_entreprise"]/span/a',
                                                             1, method='xpath').text
            advert.place = u'%s' % self.parser.select(li, 'div/span[@class="offres_ville"]/span/span/span',
                                                      1, method='xpath').text.strip()
            _date = u'%s' % self.parser.select(li, 'div/span[@class="offres_date"]',
                                               1, method='xpath').text_content()
            year = date.today().year
            splitted_date = _date.split('/')
            advert.publication_date = datetime(year, int(splitted_date[1]), int(splitted_date[0]))
            advert.contract_type = u'%s' % self.parser.select(li, 'div/span[@class="offres_poste"]/span',
                                                              1, method='xpath').text
            yield advert


class AdvertPage(BasePage):
    def get_job_advert(self, url, advert):
        re_id = re.compile('http://(.*?)/offre_emploi/detailoffre.aspx\?numoffre=(.*?)&de=consultation', re.DOTALL)
        if advert is None:
            _id = u'%s|%s' % (re_id.search(url).group(1), re_id.search(url).group(2))
            advert = RegionsJobAdvert(_id)

        advert.url = u'%s' % url

        div = self.document.getroot().xpath('//div[@id="annonce"]')[0]

        advert.title = u'%s' % self.parser.select(div, 'h1', 1, method='xpath').text

        content = self.parser.select(div, 'p', method='xpath')

        next_is_date = False
        next_is_pay = False
        description = ''

        for p in content:
            if next_is_date:
                m = re.match('(\d{2})\s(\d{2})\s(\d{4})', date)
                if m:
                    dd = int(m.group(1))
                    mm = int(m.group(2))
                    yyyy = int(m.group(3))
                    advert.publication_date = datetime.date(yyyy, mm, dd)
                next_is_date = False

            elif next_is_pay:
                advert.pay = html2text(self.parser.tostring(p))
                next_is_pay = False

            elif 'class' in p.attrib:
                if p.attrib['class'] == 'contrat_loc':
                    contrat_loc = self.parser.select(div, 'p[@class="contrat_loc"]/strong', 3, method='xpath')
                    advert.society_name = u'%s' % contrat_loc[0].text
                    advert.contract_type = u'%s' % contrat_loc[1].text
                    advert.place = u'%s' % contrat_loc[2].text
                elif p.attrib['class'] == 'date_ref':
                    next_is_date = True

                elif p.attrib['class'] == 'rubrique_annonce' and p.text == 'Salaire':
                    next_is_pay = True

                else:
                    description = description + html2text(self.parser.tostring(p))
            else:
                description = description + html2text(self.parser.tostring(p))

        advert.description = u'%s' % description

        return advert
