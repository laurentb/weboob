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

import datetime
from HTMLParser import HTMLParser
import re
from weboob.tools.browser import BasePage
from .job import IndeedJobAdvert

__all__ = ['SearchPage', 'AdvertPage']


class SearchPage(BasePage):
    def iter_job_adverts(self):
        rows = self.document.getroot().xpath('//div[@itemtype="http://schema.org/JobPosting"]')
        for row in rows:
            advert = self.create_job_advert(row)
            if advert:
                yield advert

    def create_job_advert(self, row):

        advert_from = self.parser.select(row, 'table/tr/td/div[@class="iaP"]', method='xpath')
        num_id = row.attrib['id'][2:]
        title = self.parser.select(row, 'h2/a', 1, method='xpath').attrib['title']
        society_name = self.parser.select(row, 'span[@class="company"]', 1, method='xpath').text_content().strip()
        if num_id and title and society_name and advert_from and \
           len(advert_from) > 0 and 'Indeed' in advert_from[0].text_content().strip():

            advert = IndeedJobAdvert(society_name + "|" + title + "|" + num_id)
            advert.title = u'%s' % title
            advert.society_name = u'%s' % society_name
            advert.place = u'%s' % self.parser.select(row, 'span/span[@class="location"]', 1, method='xpath').text_content().strip()

            date = self.parser.select(row, 'table/tr/td/span[@class="date"]', 1, method='xpath').text_content().strip()
            now = datetime.datetime.now()
            number = re.search("\d+", date)
            if number:
                if 'heures' in date:
                    date = now - datetime.timedelta(hours=int(number.group(0)))
                    advert.publication_date = datetime.datetime.combine(date, datetime.time())
                elif 'jour' in date:
                    date = now - datetime.timedelta(days=int(number.group(0)))
                    advert.publication_date = datetime.datetime.combine(date, datetime.time())
            return advert
        return None


class AdvertPage(BasePage):
    def get_job_advert(self, url, advert):
        job_header = self.document.getroot().xpath('//div[@id="job_header"]')[0]
        if not advert:
            title = self.parser.select(job_header, 'b[@class="jobtitle"]', 1, method='xpath').text_content()
            society_name = self.parser.select(job_header, 'span[@class="company"]', 1, method='xpath').text_content()
            num_id = url.split('-')[-1]
            advert = IndeedJobAdvert(society_name + "|" + title + "|" + num_id)

        advert.place = u'%s' % self.parser.select(job_header, 'span[@class="location"]', 1, method='xpath').text_content()
        description_content = self.document.getroot().xpath('//span[@class="summary"]')[0]
        advert.description = u'%s' % self.strip_tags(self.parser.tostring(description_content))
        advert.job_name = u'%s' % self.parser.select(job_header, 'b[@class="jobtitle"]', 1, method='xpath').text_content()
        advert.url = url

        date = self.document.getroot().xpath('//span[@class="date"]')[0].text_content().strip()
        now = datetime.datetime.now()
        number = re.search("\d+", date)
        if number:
            if 'heures' in date:
                date = now - datetime.timedelta(hours=int(number.group(0)))
                advert.publication_date = date
            elif 'jour' in date:
                date = now - datetime.timedelta(days=int(number.group(0)))
                advert.publication_date = date

        return advert

    def strip_tags(self, html):
        s = MLStripper()
        s.feed(html)
        return s.get_data()


class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)
