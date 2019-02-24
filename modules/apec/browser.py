# -*- coding: utf-8 -*-

# Copyright(C) 2013      Bezleputh
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

from weboob.browser.profiles import Profile
from weboob.browser import PagesBrowser, URL
from .pages import IdsPage, OffrePage


__all__ = ['ApecBrowser']


class JsonProfile(Profile):
    def setup_session(self, session):
        session.headers["Content-Type"] = "application/json"


class ApecBrowser(PagesBrowser):
    BASEURL = 'https://cadres.apec.fr'
    PROFILE = JsonProfile()

    start = 0
    json_count = URL('/cms/webservices/rechercheOffre/count', IdsPage)
    json_ids = URL('/cms/webservices/rechercheOffre/ids', IdsPage)
    json_offre = URL('/cms/webservices/offre/public\?numeroOffre=(?P<_id>.*)', OffrePage)

    def create_parameters(self, pattern='', fonctions='[]', lieux='[]', secteursActivite='[]', typesContrat='[]',
                          typesConvention='[]', niveauxExperience='[]', salaire_min='', salaire_max='',
                          date_publication='', start=0, range=20):

        if date_publication:
            date_publication = ',"anciennetePublication":%s' % (date_publication)

        if salaire_max:
            salaire_max = ',"salaireMaximum":%s' % (salaire_max)

        if salaire_min:
            salaire_min = ',"salaireMinimum":%s' % (salaire_min)

        return '{"activeFiltre":true,"motsCles":"%s","fonctions":%s,"lieux":%s,"pointGeolocDeReference":{},"secteursActivite":%s,"typesContrat":%s,"typesConvention":%s,"niveauxExperience":%s%s%s%s,"sorts":[{"type":"SCORE","direction":"DESCENDING"}],"pagination":{"startIndex":%s,"range":%s},"typeClient":"CADRE"}' % (pattern, fonctions, lieux, secteursActivite, typesContrat, typesConvention, niveauxExperience, salaire_min, salaire_max, date_publication, start, range)

    def search_job(self, pattern=None):
        data = self.create_parameters(pattern=pattern).encode('utf-8')
        return self.get_job_adverts(data, pattern=pattern)

    def get_job_adverts(self, data, pattern='', lieux='', fonctions='', secteursActivite='', salaire_min='',
                        salaire_max='', typesContrat='', date_publication='', niveauxExperience='', typesConvention=''):
        count = self.json_count.go(data=data).get_adverts_number()
        self.start = 0
        if count:
            ids = self.json_ids.go(data=data).iter_job_adverts(pattern=pattern,
                                                               fonctions='[%s]' % fonctions,
                                                               lieux='[%s]' % lieux,
                                                               secteursActivite='[%s]' % secteursActivite,
                                                               typesContrat='[%s]' % typesContrat,
                                                               niveauxExperience='[%s]' % niveauxExperience,
                                                               typesConvention='[%s]' % typesConvention,
                                                               salaire_min=salaire_min,
                                                               salaire_max=salaire_max,
                                                               date_publication=date_publication,
                                                               start=self.start,
                                                               count=count,
                                                               range=20)
            for _id in ids:
                yield self.json_offre.go(_id=_id.id).get_job_advert()

    def get_job_advert(self, _id, advert=None):
        return self.json_offre.go(_id=_id).get_job_advert(obj=advert)

    def advanced_search_job(self, region='', fonction='', secteur='', salaire='', contrat='', limit_date='', level=''):
        salaire_max = ''
        salaire_min = ''

        if salaire:
            s = salaire.split('|')
            salaire_max = s[1]
            salaire_min = s[0]

        data = self.create_parameters(fonctions='[%s]' % fonction,
                                      lieux='[%s]' % region,
                                      secteursActivite='[%s]' % secteur,
                                      typesContrat='[%s]' % contrat,
                                      niveauxExperience='[%s]' % level,
                                      salaire_min=salaire_min,
                                      salaire_max=salaire_max,
                                      date_publication=limit_date)

        return self.get_job_adverts(data,
                                    fonctions=fonction,
                                    lieux=region,
                                    secteursActivite=secteur,
                                    typesContrat=contrat,
                                    niveauxExperience=level,
                                    salaire_min=salaire_min,
                                    salaire_max=salaire_max,
                                    date_publication=limit_date)
