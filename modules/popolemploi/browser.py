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

from urllib import quote_plus, quote

__all__ = ['PopolemploiBrowser']


class PopolemploiBrowser(PagesBrowser):

    BASEURL = 'http://candidat.pole-emploi.fr/'

    advert = URL('candidat/rechercheoffres/detail/(?P<id>.*)', AdvertPage)
    search = URL('candidat/rechercheoffres/resultats/(?P<search>.*?)',
                 'http://offre.pole-emploi.fr/resultat\?offresPartenaires=true&libMetier=(?P<pattern>.*?)', SearchPage)

    def search_job(self, pattern=None):
        return self.search.go(pattern=quote_plus(pattern)).iter_job_adverts()

    def advanced_search_job(self, metier='', place=None, contrat=None, salary=None,
                            qualification=None, limit_date=None, domain=None):

        splitted_place = place.split('|')

        search = 'A_%s_%s_%s__%s_P_%s_%s_%s_______INDIFFERENT______________%s___' % (quote(metier.encode('utf-8')).replace('%', '$00'),
                                                                                     splitted_place[1],
                                                                                     splitted_place[2],
                                                                                     contrat,
                                                                                     domain,
                                                                                     salary,
                                                                                     qualification,
                                                                                     limit_date
                                                                                     )

        return self.search.go(search=search).iter_job_adverts()

    def get_job_advert(self, id, advert):
        return self.advert.go(id=id).get_job_advert(obj=advert)
