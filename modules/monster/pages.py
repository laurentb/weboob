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


import re
from datetime import datetime, time, timedelta

from weboob.browser.pages import HTMLPage, pagination
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.standard import CleanText, Regexp, Filter, Env, BrowserURL, Join
from weboob.browser.filters.html import Link, CleanHTML
from weboob.capabilities.job import BaseJobAdvert
from weboob.capabilities.base import NotAvailable


class MonsterDate(Filter):
    def filter(self, date):
        now = datetime.now()
        number = re.search("\d+", date)
        if number:
            if 'heures' in date:
                date = now - timedelta(hours=int(number.group(0)))
                return datetime.combine(date, time())
            elif 'jour' in date:
                date = now - timedelta(days=int(number.group(0)))
                return datetime.combine(date, time())
        else:
            return datetime.combine(now, time.min)


class SearchPage(HTMLPage):
    @pagination
    @method
    class iter_job_adverts(ListElement):
        item_xpath = '//table[@class="listingsTable"]/tbody/tr[@class="odd"] | //table[@class="listingsTable"]/tbody/tr[@class="even"]'

        def next_page(self):
            return Link('//a[@title="Suivant"]', default=None)(self)

        class item(ItemElement):
            klass = BaseJobAdvert

            obj_id = Regexp(Link('./td/div/div[@class="jobTitleContainer"]/a'),
                            'http://offre-emploi.monster.fr:80/(.*?).aspx')
            obj_society_name = CleanText('./td/div/div[@class="companyContainer"]/div/a')
            obj_title = CleanText('./td/div/div[@class="jobTitleContainer"]/a')
            obj_publication_date = MonsterDate(CleanText('td/div/div[@class="fnt20"]'))
            obj_place = CleanText('./td/div/div[@class="jobLocationSingleLine"]/a/@title', default=NotAvailable)


class AdvertPage(HTMLPage):
    @method
    class get_job_advert(ItemElement):
        klass = BaseJobAdvert

        obj_id = Env('_id')
        obj_url = BrowserURL('advert', _id=Env('_id'))
        obj_title = CleanText('//div[@id="jobcopy"]/h1[@itemprop="title"]|//div[@itemprop="title"]/h1')
        obj_description = CleanHTML('//div[@id="jobBodyContent"]|//div[@itemprop="description"]')
        obj_contract_type = Join('%s ', '//dd[starts-with(@class, "multipledd")]')
        obj_society_name = CleanText('//dd[@itemprop="hiringOrganization"]')
        obj_place = CleanText('//span[@itemprop="jobLocation"]')
        obj_pay = CleanText('//span[@itemprop="baseSalary"]')
        obj_formation = CleanText('//span[@itemprop="educationRequirements"]')
        obj_experience = CleanText('//span[@itemprop="qualifications"]')
