# -*- coding: utf-8 -*-

# Copyright(C) 2016      François Revol
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


from weboob.capabilities.job import BaseJobAdvert
from weboob.browser.pages import HTMLPage
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.standard import Regexp, CleanText, Date, Env, BrowserURL
from weboob.browser.filters.html import Link, CleanHTML

class AdvertPage(HTMLPage):
    @method
    class get_job_advert(ItemElement):
        klass = BaseJobAdvert

        obj_id = Env('id')
        obj_url = BrowserURL('advert_page', id=Env('id'))
        obj_title = CleanText('//title')
        obj_job_name = CleanText('//title')


class SearchPage(HTMLPage):
    @method
    class iter_job_adverts(ListElement):
        item_xpath = '//a[@class="list-group-item "]'

        class item(ItemElement):
            klass = BaseJobAdvert

            obj_id = Regexp(Link('.'), '.*fr/jobs/(\d+)/.*')
            obj_title = CleanText('h4/span[@class="job-title"]')
            obj_society_name = CleanText('h4/span[@class="job-company"]')
