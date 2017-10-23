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

from datetime import timedelta, datetime
import re
from weboob.browser.pages import HTMLPage, pagination
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import Filter, CleanText, Regexp, Format, Env
from weboob.browser.filters.html import CleanHTML, Attr
from weboob.capabilities.job import BaseJobAdvert


class IndeedDate(Filter):
    def filter(self, date):
        now = datetime.now()
        number = re.search("\d+", date)
        if number:
            if 'heures' in date:
                return now - timedelta(hours=int(number.group(0)))
            elif 'jour' in date:
                return now - timedelta(days=int(number.group(0)))
        return now


class SearchPage(HTMLPage):
    @pagination
    @method
    class iter_job_adverts(ListElement):
        item_xpath = '//div[@data-tn-component="organicJob"]'

        def next_page(self):
            for a in self.page.doc.xpath('//a'):
                if a.xpath('span[@class="pn"]/span[@class="np"]') and "Suivant" in a.xpath('span[@class="pn"]/span[@class="np"]')[0].text:
                    return a.attrib['href']

        class Item(ItemElement):
            klass = BaseJobAdvert

            obj_id = CleanText(Format('%s#%s#%s',
                                      Regexp(Attr('.', 'id'), '^..(.*)'),
                                      Attr('h2/a', 'title'),
                                      CleanText('span[@class="company"]')),
                               replace=[(" ", "-"), ("/", "-")])
            obj_title = Attr('h2/a', 'title')
            obj_society_name = CleanText('span[@class="company"]')
            obj_place = CleanText('span/span[@class="location"]')
            obj_publication_date = IndeedDate(CleanText('table/tr/td/span[@class="date"]'))


class AdvertPage(HTMLPage):

    @method
    class get_job_advert(ItemElement):
        klass = BaseJobAdvert

        def parse(self, el):
            self.env['url'] = self.page.url
            self.env['num_id'] = self.page.url.split('-')[-1]

        obj_id = Format('%s#%s#%s',
                        Env('num_id'),
                        CleanText('//div[@id="job_header"]/b[@class="jobtitle"]'),
                        CleanText('//div[@id="job_header"]/span[@class="company"]'),
                        )
        obj_title = CleanText('//div[@id="job_header"]/b[@class="jobtitle"]')
        obj_place = CleanText('//div[@id="job_header"]/span[@class="location"]')
        obj_description = CleanHTML('//span[@class="summary"]')
        obj_job_name = CleanText('//div[@id="job_header"]/b[@class="jobtitle"]')
        obj_url = Env('url')
        obj_publication_date = IndeedDate(CleanText('//span[@class="date"]'))
