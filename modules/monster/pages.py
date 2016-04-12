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
from weboob.browser.filters.standard import CleanText, Regexp, Filter, Env, BrowserURL, Join, Date, Format, DateTime
from weboob.browser.filters.html import CleanHTML
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


class AdvSearchPage(HTMLPage):
    @pagination
    @method
    class iter_job_adverts(ListElement):
        item_xpath = '//article[@class="js_result_row"]'

        def next_page(self):
            page = Regexp(CleanText('//link[@rel="next"]/@href', default=''),
                          '.*page=(\d*)', default=None)(self)
            if page:
                return BrowserURL('adv_search', search=Env('search'), page=int(page))(self)

        class item(ItemElement):

            def condition(self):
                return u'Désolé' not in CleanText('//h1')(self)

            klass = BaseJobAdvert

            obj_id = Regexp(CleanText('./div[@class="jobTitle"]/h2/a/@href'),
                            'http://offre-(d?)emploi.monster.fr/(.*?)(.aspx|\?).*',
                            '\\1#\\2')
            obj_society_name = CleanText('./div[@class="company"]/span[@itemprop="name"]',
                                         replace=[(u'Trouvée sur : ', u'')],
                                         default=NotAvailable)
            obj_title = CleanText('./div[@class="jobTitle"]/h2/a/span[@itemprop="title"]',
                                  default=NotAvailable)
            obj_publication_date = DateTime(CleanText('./div[@class="extras"]/div[@class="postedDate"]/time/@datetime'),
                                            default=NotAvailable)
            obj_place = CleanText('./div[@class="location"]/span[@itemprop="name"]',
                                  default=NotAvailable)


class AdvertPage(HTMLPage):
    @method
    class get_job_advert(ItemElement):
        klass = BaseJobAdvert

        obj_id = Format('#%s', Env('_id'))
        obj_url = BrowserURL('advert', _id=Env('_id'))
        obj_title = CleanText('//div[@id="jobcopy"]/h1[@itemprop="title"]|//div[@itemprop="title"]/h1')
        obj_description = CleanHTML('//div[@id="jobBodyContent"]|//div[@itemprop="description"]')
        obj_contract_type = Join(u' ', '//dd[starts-with(@class, "multipledd")]')
        obj_society_name = CleanText('//dd[@itemprop="hiringOrganization"]')
        obj_place = CleanText('//span[@itemprop="jobLocation"]')
        obj_pay = CleanText('//span[@itemprop="baseSalary"]')
        obj_formation = CleanText('//span[@itemprop="educationRequirements"]')
        obj_experience = CleanText('//span[@itemprop="qualifications"]')


class AdvertPage2(HTMLPage):
    @method
    class get_job_advert(ItemElement):
        klass = BaseJobAdvert

        obj_id = Format('d#%s', Env('_id'))
        obj_url = BrowserURL('advert2', _id=Env('_id'))
        obj_title = CleanText('//h3')
        obj_description = CleanHTML('//div[@id="jobBodyContent"]|//div[@itemprop="description"]')
        obj_contract_type = CleanHTML('//div[@class="jobview-section"]')
        obj_society_name = Regexp(CleanText('//h4[@class="company"]'),
                                  '.* : (.*) - .*')
        obj_place = Regexp(CleanText('//h4[@class="company"]'),
                           '.* - (.*)')
        obj_publication_date = Date(Regexp(CleanText('//span[@class="postedDate"]'),
                                           '.* : (.*)'),
                                    dayfirst=True)
