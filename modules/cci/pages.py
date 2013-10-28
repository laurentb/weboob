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

import dateutil.parser

from weboob.tools.browser import BasePage
from weboob.capabilities.job import BaseJobAdvert

__all__ = ['SearchPage']


class SearchPage(BasePage):
    def iter_job_adverts(self, pattern):
        trs = self.document.getroot().xpath("//tr[@class='texteCol2TableauClair']") \
            + self.document.getroot().xpath("//tr[@class='texteCol2TableauFonce']")

        for tr in trs:
            tds = self.parser.select(tr, 'td', method='xpath')
            a = self.parser.select(tds[2], 'a', 1, method='xpath')
            advert = BaseJobAdvert(a.attrib['href'].replace('#', ''))
            advert.title = u'%s' % a.text_content()
            advert.society_name = u'CCI %s' % tds[3].text
            advert.place = u'%s' % tds[0].text
            advert.job_name = u'%s' % tds[1].text
            if pattern is not None:
                if pattern in advert.title or pattern in advert.job_name:
                    yield advert
            else:
                yield advert

    def get_job_advert(self, _id, advert):
        if advert is None:
            advert = BaseJobAdvert(_id)

        items = self.document.getroot().xpath("//div[@id='divrecueil']")[0]
        keep_next = False
        for item in items:

            if keep_next:
                if item.tag == 'div' and item.attrib['id'] == u'offre':
                    first_div = self.parser.select(item, 'div/span', 2, method='xpath')
                    advert.society_name = u'CCI %s' % first_div[0].text_content()
                    advert.job_name = u'%s' % first_div[1].text_content()

                    second_div = self.parser.select(item, 'div/fieldset', 2, method='xpath')

                    ps_1 = self.parser.select(second_div[0], 'p[@class="normal"]', method='xpath')
                    h2s_1 = self.parser.select(second_div[0], 'h2[@class="titreParagraphe"]', method='xpath')
                    description = ""
                    if len(ps_1) == 5 and len(h2s_1) == 5:
                        for i in range(0, 5):
                            description += "\r\n-- %s --\r\n" % h2s_1[i].text
                            description += "%s\r\n" % ps_1[i].text_content()
                    advert.description = description
                    advert.url = self.url + '#' + advert.id
                    date = self.parser.select(item, 'div/fieldset/p[@class="dateOffre"]', 1, method='xpath')
                    advert.publication_date = dateutil.parser.parse(date.text_content()).date()
                break

            if item.tag == 'a' and u'%s' % item.attrib['name'] == u'%s' % _id:
                keep_next = True

        return advert
