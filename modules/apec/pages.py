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
import dateutil.parser
import re

from .job import ApecJobAdvert


class SearchPage(Page):
    def iter_job_adverts(self):
        re_id_title = re.compile('/offres-emploi-cadres/\d*_\d*_\d*_(.*?)_(.*?)_(.*?)_(.*?)_(.*?)_(.*?)_(.*?)_(.*?)_(.*?).html', re.DOTALL)
        divs = self.document.getroot().xpath("//div[@class='boxContent offre']") + self.document.getroot().xpath("//div[@class='boxContent offre even']")
        for div in divs:
            a = self.parser.select(div, 'div/div/h3/a', 1, method='xpath')
            _id = u'%s/%s' % (re_id_title.search(a.attrib['href']).group(1), re_id_title.search(a.attrib['href']).group(9))
            advert = ApecJobAdvert(_id)
            advert.title = u'%s' % re_id_title.search(a.attrib['href']).group(9).replace('-', ' ')
            l = self.parser.select(div, 'h4', 1).text.split('-')
            advert.society_name = u'%s' % l[0].strip()
            advert.place = u'%s' % l[-1].strip()
            date = self.parser.select(div, 'div/div/div', 1, method='xpath')
            advert.publication_date = dateutil.parser.parse(date.text_content().strip()[8:]).date()
            yield advert


class AdvertPage(Page):
    def get_job_advert(self, url, advert):
        re_id_title = re.compile('/offres-emploi-cadres/\d*_\d*_\d*_(.*?)________(.*?).html(.*?)', re.DOTALL)
        if advert is None:
            _id = u'%s/%s' % (re_id_title.search(url).group(1), re_id_title.search(url).group(2))
            advert = ApecJobAdvert(_id)
            advert.title = re_id_title.search(url).group(2).replace('-', ' ')

        description = self.document.getroot().xpath("//div[@class='contentWithDashedBorderTop marginTop boxContent']/div")[0]
        advert.description = html2text(self.parser.tostring(description))

        advert.job_name = advert.title

        trs = self.document.getroot().xpath("//table[@class='noFieldsTable']/tr")
        for tr in trs:
            th = self.parser.select(tr, 'th', 1, method='xpath')
            td = self.parser.select(tr, 'td', 1, method='xpath')
            if u'Date de publication' in u'%s' % th.text_content():
                advert.publication_date = dateutil.parser.parse(td.text_content()).date()
            elif u'Société' in u'%s' % th.text_content() and not advert.society_name:
                society_name = td.text_content()
                a = self.parser.select(td, 'a', method='xpath')
                if a:
                    advert.society_name = u'%s' % society_name.replace(a[0].text_content(), '').strip()
                else:
                    advert.society_name = society_name.strip()
            elif u'Type de contrat' in u'%s' % th.text_content():
                advert.contract_type = u'%s' % td.text_content().strip()
            elif u'Lieu' in u'%s' % th.text_content():
                advert.place = u'%s' % td.text_content()
            elif u'Salaire' in u'%s' % th.text_content():
                advert.pay = u'%s' % td.text_content()
            elif u'Expérience' in u'%s' % th.text_content():
                advert.experience = u'%s' % td.text_content()

        advert.url = url
        return advert
