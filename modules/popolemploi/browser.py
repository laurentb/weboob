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

from .pages import SearchPage, AdvertPage
from weboob.browser import PagesBrowser, URL
from weboob.tools.compat import quote

__all__ = ['PopolemploiBrowser']


class PopolemploiBrowser(PagesBrowser):

    BASEURL = 'https://candidat.pole-emploi.fr/'

    advert = URL('candidat/rechercheoffres/detail/(?P<id>.*)', AdvertPage)
    search = URL('candidat/rechercheoffres/resultats/(?P<search>.*?)', SearchPage)

    decode_salary = {
        'FOURCHETTE1': u'|15000|A',
        'FOURCHETTE2': u'15000|18000|A',
        'FOURCHETTE3': u'18000|21000|A',
        'FOURCHETTE4': u'21000|24000|A',
        'FOURCHETTE5': u'24000|36000|A',
        'FOURCHETTE6': u'36000|60000|A',
        'FOURCHETTE7': u'60000||A',
    }

    def search_job(self, pattern=None):
        search = "A_%s_____P__________INDIFFERENT_______________________" % \
                 quote(pattern.encode('utf-8')).replace('%', '$00')
        return self.search.go(search=search).iter_job_adverts()

    def advanced_search_job(self, metier='', place=None, contrat=None, salary=None,
                            qualification=None, limit_date=None, domain=None):

        splitted_place = place.split('|')
        _domain = "%s-" % domain if domain else ""

        if salary in self.decode_salary:
            salary_time = self.decode_salary.get(salary).split('|')[2]
            salary_low = self.decode_salary.get(salary).split('|')[0]
            salary_hight = self.decode_salary.get(salary).split('|')[1]
        else:
            salary_time = ""
            salary_low = ""
            salary_hight = ""

        search = "A_%s_%s_%s__%s_P_%s_%s_%s_____________________%s_%s_%s_______" % (
            quote(metier.encode('utf-8')).replace('%', '$00'),
            splitted_place[1],
            splitted_place[2],
            contrat,
            _domain,
            salary_time,
            qualification,
            limit_date,
            salary_low,
            salary_hight)
        return self.search.go(search=search).iter_job_adverts()

    def get_job_advert(self, id, advert):
        return self.advert.go(id=id).get_job_advert(obj=advert)
