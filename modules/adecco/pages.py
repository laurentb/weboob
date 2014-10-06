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
from weboob.tools.html import html2text
from .job import AdeccoJobAdvert
import datetime
import re

MONTHS = [u'janvier', u'février', u'mars', u'avril', u'mai', u'juin', u'juillet', u'août', u'septembre', u'octobre', u'novembre', u'décembre']


class SearchPage(Page):
    def iter_job_adverts(self):
        re_id = re.compile('http://www.adecco.fr/trouver-un-emploi/Pages/Details-de-l-Offre/(.*?)/(.*?).aspx\?IOF=(.*?)$', re.DOTALL)

        divs = self.document.getroot().xpath("//div[@class='resultContain right']") + self.document.getroot().xpath("//div[@class='resultContain left']")

        for div in divs:

            a = self.parser.select(div, 'div/a', 1, method='xpath').attrib['href']
            if re_id.match(a):

                _id = u'%s/%s/%s' % (re_id.search(a).group(1), re_id.search(a).group(2), re_id.search(a).group(3))

                advert = AdeccoJobAdvert(_id)

                date = u'%s' % self.parser.select(div, "div/span[@class='offreDatePublication']", 1, method='xpath').text
                m = re.match('(\d{2})\s(.*?)\s(\d{4})', date)
                if m:
                    dd = int(m.group(1))
                    mm = MONTHS.index(m.group(2)) + 1
                    yyyy = int(m.group(3))
                    advert.publication_date = datetime.date(yyyy, mm, dd)

                advert.title = u'%s' % self.parser.select(div, "div/h3/a", 1, method='xpath').text_content()
                advert.place = u'%s' % self.parser.select(div, "div/h3/span[@class='offreLocalisation']", 1, method='xpath').text
                yield advert


class AdvertPage(Page):
    def get_job_advert(self, url, advert):
        re_id = re.compile('http://www.adecco.fr/trouver-un-emploi/Pages/Details-de-l-Offre/(.*?)/(.*?).aspx\?IOF=(.*?)$', re.DOTALL)
        if advert is None:
            _id = u'%s/%s/%s' % (re_id.search(url).group(1), re_id.search(url).group(2), re_id.search(url).group(3))
            advert = AdeccoJobAdvert(_id)

        advert.contract_type = re_id.search(url).group(1)
        div = self.document.getroot().xpath("//div[@class='contain_MoreResults']")[0]

        date = u'%s' % self.parser.select(div, "div[@class='dateResult']", 1, method='xpath').text.strip()
        m = re.match('(\d{2})\s(.*?)\s(\d{4})', date)
        if m:
            dd = int(m.group(1))
            mm = MONTHS.index(m.group(2)) + 1
            yyyy = int(m.group(3))
            advert.publication_date = datetime.date(yyyy, mm, dd)

        title = self.parser.select(div, "h1", 1, method='xpath').text_content().strip()
        town = self.parser.select(div, "h1/span/span[@class='town']", 1, method='xpath').text_content()
        page_title = self.parser.select(div, "h1/span[@class='pageTitle']", 1, method='xpath').text_content()
        advert.title = u'%s' % title.replace(town, '').replace(page_title, '')

        spans = self.document.getroot().xpath("//div[@class='jobGreyContain']/table/tr/td/span[@class='value']")
        advert.job_name = u'%s' % spans[0].text
        advert.place = u'%s' % spans[1].text
        advert.pay = u'%s' % spans[2].text
        advert.contract_type = u'%s' % spans[3].text
        advert.url = url
        description = self.document.getroot().xpath("//div[@class='descriptionContainer']/p")[0]
        advert.description = html2text(self.parser.tostring(description))
        return advert
