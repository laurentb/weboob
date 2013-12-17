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


from weboob.tools.browser import BasePage
from weboob.tools.misc import html2text
import re
from datetime import datetime, time, timedelta
from .job import MonsterJobAdvert

__all__ = ['SearchPage', 'AdvertPage']


class SearchPage(BasePage):
    def iter_job_adverts(self):
        re_id = re.compile('http://offre-emploi.monster.fr/(.*?).aspx', re.DOTALL)
        trs = self.document.getroot().xpath("//table[@class='listingsTable']/tbody/tr")
        for tr in trs:
            if 'class' in tr.attrib and tr.attrib['class'] != 'aceHidden':
                a = self.parser.select(tr, 'td/div/div[@class="jobTitleContainer"]/a', 1, method='xpath')
                _id = u'%s' % re_id.search(a.attrib['href']).group(1)
                advert = MonsterJobAdvert(_id)
                advert.society_name = u'%s' % self.parser.select(tr, 'td/div/div[@class="companyContainer"]/div/a',
                                                                 1, method='xpath').attrib['title']
                advert.title = u'%s' % a.text

                date = self.parser.select(tr, 'td/div/div[@class="fnt20"]', 1, method='xpath').text_content().strip()
                now = datetime.now()
                number = re.search("\d+", date)
                if number:
                    if 'heures' in date:
                        date = now - timedelta(hours=int(number.group(0)))
                        advert.publication_date = datetime.combine(date, time())
                    elif 'jour' in date:
                        date = now - timedelta(days=int(number.group(0)))
                        advert.publication_date = datetime.combine(date, time())
                else:
                    advert.publication_date = datetime.combine(now, time.min)

                place = self.parser.select(tr, 'td/div/div[@class="jobLocationSingleLine"]/a', method='xpath')
                if len(place) != 0:
                    advert.place = u'%s' % place[0].attrib['title']

                yield advert


class AdvertPage(BasePage):
    def get_job_advert(self, url, advert):
        re_id = re.compile('http://offre-emploi.monster.fr/(.*?).aspx', re.DOTALL)
        if advert is None:
            _id = u'%s' % re_id.search(url).group(1)
            advert = MonsterJobAdvert(_id)

        div = self.document.getroot().xpath('//div[@id="jobcopy"]')[0]
        advert.title = u'%s' % self.parser.select(div, 'h1', 1, method='xpath').text
        description = self.parser.select(div, 'div[@id="jobBodyContent"]', 1, method='xpath')
        advert.description = html2text(self.parser.tostring(description))

        jobsummary = self.document.getroot().xpath('//div[@id="jobsummary_content"]')[0]

        society_name = self.parser.select(jobsummary, 'dl/dd/span[@itemprop="name"]', method='xpath')
        if len(society_name) != 0:
            advert.society_name = u'%s' % society_name[0].text

        place = self.parser.select(jobsummary, 'dl/dd/span[@itemprop="jobLocation"]', method='xpath')
        if len(place) != 0:
            advert.place = u'%s' % place[0].text

        contract_type = self.parser.select(jobsummary, 'dl/dd[@class="multipleddlast"]/span', method='xpath')
        if len(contract_type) != 0:
            advert.contract_type = u'%s' % contract_type[0].text

        pay = self.parser.select(jobsummary, 'dl/dd/span[@itemprop="baseSalary"]', method='xpath')
        if len(pay) != 0:
            advert.pay = u'%s' % pay[0].text

        formation = self.parser.select(jobsummary, 'dl/dd/span[@itemprop="educationRequirements"]', method='xpath')
        if len(formation) != 0:
            advert.formation = u'%s' % formation[0].text

        advert.experience = u'%s' % self.parser.select(jobsummary, 'dl/dd/span[@itemprop="qualifications"]', 1, method='xpath').text
        advert.url = url
        return advert
