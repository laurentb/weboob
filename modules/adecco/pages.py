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


from weboob.browser.pages import HTMLPage, pagination
from weboob.browser.elements import ItemElement, ListElement, method

from weboob.browser.filters.standard import CleanText, Regexp, DateTime
from weboob.browser.filters.html import CleanHTML

from weboob.capabilities.job import BaseJobAdvert

from weboob.tools.date import DATE_TRANSLATE_FR


class SearchPage(HTMLPage):
    @pagination
    @method
    class iter_job_adverts(ListElement):
        item_xpath = '//div[has-class("resultContain")]'

        def next_page(self):
            next_page = CleanText('(//a[@class="next enabled"])[1]/@href',
                                  default=None)(self)
            if next_page:
                return next_page

        class item(ItemElement):
            klass = BaseJobAdvert

            def validate(self, obj):
                return obj.id

            obj_id = Regexp(CleanText('./div/h3/a/@href'),
                            'http://www.adecco.fr/trouver-un-emploi/Pages/Details-de-l-Offre/(.*)/(.*)\.aspx\?IOF=(.*)',
                            '\\1/\\2/\\3',
                            default=None)
            obj_title = CleanText('./div/h3/a')
            obj_place = CleanText('./div/h3/span[@class="offreLocalisation"]')
            obj_publication_date = DateTime(Regexp(CleanText('./div/span[@class="offreDatePublication"]'),
                                                   u'Publiée le (.*)'),
                                            translations=DATE_TRANSLATE_FR)


class AdvertPage(HTMLPage):
    @method
    class get_job_advert(ItemElement):
        klass = BaseJobAdvert

        obj_id = Regexp(CleanText('//meta[@property="og:url"]/@content'),
                        'http://www.adecco.fr/trouver-un-emploi/Pages/Details-de-l-Offre/(.*)/(.*)\.aspx\?IOF=(.*)',
                        '\\1/\\2/\\3',
                        default=None)

        obj_title = CleanText('//span[@class="titleContainer"]')

        obj_place = CleanText('//div[@class="jobGreyContain"]/div/div[1]/span[@class="value"]')

        obj_contract_type = CleanText('//div[@class="jobGreyContain"]/div/div[2]/span[@class="value"]')

        obj_pay = CleanText('//div[@class="jobGreyContain"]/div/div[4]/span[@class="value"]')

        obj_job_name = CleanText('//span[@class="titleContainer"]')
        obj_description = CleanHTML('//p[@itemprop="responsibilities"]')
        obj_url = CleanText('//meta[@property="og:url"]/@content')
