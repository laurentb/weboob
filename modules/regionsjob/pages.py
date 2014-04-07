# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
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

from weboob.tools.browser2.page import HTMLPage, method, ItemElement, SkipItem, ListElement
from weboob.tools.browser2.filters import Link, CleanText, Regexp, Format, Env, DateGuesser, CleanHTML, DateTime
from weboob.tools.date import LinearDateGuesser
from weboob.capabilities.job import BaseJobAdvert

__all__ = ['SearchPage']


class SearchPage(HTMLPage):
    @method
    class iter_job_adverts(ListElement):
        item_xpath = '//div[@id="liste_offres"]/ul/li'

        class item(ItemElement):
            klass = BaseJobAdvert

            obj_id = Format(u'%s#%s',
                            Env('domain'),
                            Regexp(Link('div/span[@class="offres_poste"]/a'), '.*?numoffre=(.*?)&de=consultation'))
            obj_title = CleanText('div/span[@class="offres_poste"]/a')
            obj_society_name = CleanText('div/span[@class="offres_entreprise"]/span/a')
            obj_place = CleanText('div/span[@class="offres_ville"]/span/span/span')
            obj_contract_type = CleanText('div/span[@class="offres_poste"]/span')
            obj_publication_date = DateGuesser(CleanText('div/span[@class="offres_date"]'), LinearDateGuesser())


class AdvertPage(HTMLPage):
    @method
    class get_job_advert(ItemElement):
        klass = BaseJobAdvert

        def parse(self, el):
            if self.obj.id:
                advert = self.obj
                advert.url = self.page.url
                advert.description = Format(u'%s\r\n%s',
                                            CleanHTML('//div[@id="annonce"]/p[@id="description_annonce"]'),
                                            CleanHTML('//div[@id="annonce"]/p[@id="description_annonce"]/following-sibling::p[1]'))(el)
                advert.pay = CleanText('//div[@id="annonce"]/p[@class="rubrique_annonce"]/following-sibling::p[1]')(el)
                raise SkipItem()

            self.env['url'] = self.page.url

        obj_description = Format(u'%s%s',
                                 CleanHTML('//div[@id="annonce"]/p[@id="description_annonce"]'),
                                 CleanHTML('//div[@id="annonce"]/p[@id="description_annonce"]/following-sibling::p[1]'))

        obj_id = Env('_id')
        obj_url = Env('url')
        obj_publication_date = DateTime(Regexp(CleanText('//div[@id="annonce"]/p[@class="date_ref"]'),
                                               '(\d{2}/\d{2}/\d{4})'))
        obj_title = CleanText('//div[@id="annonce"]/h1')
        obj_society_name = CleanText('//div[@id="annonce"]/p[@class="contrat_loc"]/strong[1]')
        obj_contract_type = CleanText('//div[@id="annonce"]/p[@class="contrat_loc"]/strong[2]')
        obj_place = CleanText('//div[@id="annonce"]/p[@class="contrat_loc"]/strong[3]')
        obj_pay = CleanText('//div[@id="annonce"]/p[@class="rubrique_annonce"]/following-sibling::p[1]')
