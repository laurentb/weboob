# -*- coding: utf-8 -*-

# Copyright(C) 2016      François Revol
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from weboob.capabilities.job import BaseJobAdvert
from weboob.browser.pages import HTMLPage
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.standard import Regexp, CleanText, Date, Env, BrowserURL
from weboob.browser.filters.html import Link, CleanHTML
from weboob.tools.date import parse_french_date

class AdvertPage(HTMLPage):
    @method
    class get_job_advert(ItemElement):
        klass = BaseJobAdvert

        obj_id = Env('id')
        obj_url = BrowserURL('advert_page', id=Env('id'))
        obj_title = CleanText('//title')
        obj_job_name = CleanText('//title')
        obj_society_name = CleanText('//div[2]/div[@class="col-md-9"]/h4[1]')
        obj_publication_date = Date(CleanText('//div[2]/div[@class="col-md-9"]/small', replace=[(u'Ajoutée le', '')]), parse_func=parse_french_date)
        obj_place = Regexp(CleanText('//div[2]/div[@class="col-md-9"]/h4[2]'), '(.*) \(.*\)')
        obj_description = CleanHTML('//div[4]/div[@class="col-md-9"]')


class SearchPage(HTMLPage):
    @method
    class iter_job_adverts(ListElement):
        item_xpath = '//a[@class="list-group-item "]'

        class item(ItemElement):
            klass = BaseJobAdvert

            obj_id = Regexp(Link('.'), '.*fr/jobs/(\d+)/.*')
            obj_title = CleanText('h4/span[@class="job-title"]')
            obj_society_name = CleanText('h4/span[@class="job-company"]')
            obj_publication_date = Date(CleanText('h4/span[@class="badge pull-right"]'), parse_func=parse_french_date)
