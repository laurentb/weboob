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

from weboob.tools.browser.decorators import id2url
from weboob.tools.browser import BaseBrowser
import re
import urllib
import copy

from .pages import SearchPage, AdvertPage, ChangeLocationReturnPage, ChangeLocationPage
from .job import PopolemploiJobAdvert


__all__ = ['PopolemploiBrowser']


class PopolemploiBrowser(BaseBrowser):
    PROTOCOL = 'http'
    DOMAIN = 'http://www.pole-emploi.fr/accueil/'
    ENCODING = None

    PAGES = {
        'http://candidat.pole-emploi.fr/candidat/rechercheoffres/avancee.recherche': ChangeLocationPage,
        'http://candidat.pole-emploi.fr/candidat/rechercheoffres/avancee/(.*?)': ChangeLocationReturnPage,
        'http://candidat.pole-emploi.fr/candidat/rechercheoffres/resultats(.*?)': SearchPage,
        'http://candidat.pole-emploi.fr/candidat/rechercheoffres/detail/(?P<id>.+)': AdvertPage,
    }

    def search_job(self, pattern=None):
        self.location('http://offre.pole-emploi.fr/resultat?offresPartenaires=true&libMetier=%s'
                      % pattern.replace(' ', '+'))
        assert self.is_on_page(SearchPage)
        return self.page.iter_job_adverts()

    def advanced_search_job(self, metier='', place=None, contrat=None, salary=None,
                            qualification=None, limit_date=None, domain=None):

        data = {
            't:formdata': 'H4sIAAAAAAAAALVYz2/cRBj9sqilZFtafkkICSQgvSEn67YQkqZlu9lWgNNEXcolBzTr/XYzxfaYmfGue4ETR5A4I3HiiCoB9x7oASkHDvwH/AGckDiBxIxnbSfbJu16TKREyvM3b957M54Zzw9/wonJKrzN0d9Drn7ZcMhRLLfHJPIR10gQIB8jFwEpSgQN44AOKaLgsDPkToxO6Ds+C8MkciSJUUh+16F7ocZiFmEkhePR6NNe0g+pbI/R77BIYipxaYczH4XInghBWXT7yx/vbTRff7UBjV142jd1El7Y9e6QMVkOSDRa3u7fQV+ue9DEAENFf5OEKOH5AyU9yWk0Wk85nNOgo0HHtIPyJ41jCa9lJj9WJj1yKzfZK0xOrsDlo+IpcGKAzK8gkXQ4GVA24iyJVUirjI8cEhNVWORzSYXDMaD9gyHd0q1u6FZLPZRJ/M3K/bd+fvavXxqwoMzqMDgLtNnP4HNopPrvUxIWy85qEHuxgtjWfrq//1Pv3/sNlWmmarIGq/MLEShbKy0l4tKxIvpEoNPuK5D48jrFYGDiOn/7QfOPl3795/i4TppeLBW251X40Ex/cG9wcfj3d7/ZZ+YqRZqhacy5FuZUW810dvIeXJmfYMRJNBiwkNAIc0WnM3DTgPa0Rt1N8OxolqYrh8iWJDWenWMXspCmNBJO1zQy69jDI/rtF199/f327u9q7fLglB9QVfv+IJt85Vqm/13I5+KhcOLJVdioMGosETOZNzWWR25LahJ/F96Zn0XuqbxyUSey/yyIjJAb0K3YfmbMNd2Luax40oH2/LzTiGLCD1k9O8V3CP8oM10HubFfaTSjJETOTHk+RQy2rTFrUoslI2QDvc1y9bIkmTZQW/LpHPUUWk2dvBtjtgMQWVjWWMdg1qTG8hZ8aMXy6Cl5UGg8uQxrFd5fRezLT1Zy76dywI7OuO5CZ36KIUs0LiUKEhBazsTnyic986SmDoxYG7+t2fhadnQWivYw4RiStFCUAVsktaMziiqdGjGNkastzjcjeVIdREvIllIzLk424dr8JGMSaHOH1anEzpkH3VJjLfQWCSYRlThQZIXGxQza1JAtpdHVhqsVNh7dHqeHmlzamQztTtEaiC1OckK9TWoQ1NmajpVftYByjDkVWLywr0xL2tOSbllSd5f/hw/38T7curu0Xy7d2eXStaOzV3RhVtEFOzoLRfoGIkFRbik5YEdn8ZpHdIwkMUSFrDMG9QxaA7F9ZO5sZBWnVd66psjcR0bm1kBsBG7AeoWzpfrCHOr7hlzcMwViSWhEefBBhful4upQcqqWn5BJ4Qfq03mq8eWioGcKtlRBRxXU251xcB7ePIpSf2lhlJ1Ni2+GA9gTNjXdLMEbj1XOBYfrT3qBeo0lkkVHXT2U16YLh69FZ24Ki67/A14oWbX6FQAA',
            'radiogroup': u'MOTS_CLES',
            'set101': metier,
            'set201': u'',
            'grandDomaine': u'',
            'sousDomaine': u'',
            'theme': u'',
            'domaineParTheme': u'',
            'numeroOffre': u'',
            'lieu': u'',
            'lieuCode': u'',
            'lieuCodePostal': u'',
            'lieuType': u'',
            'typeContrat': contrat,
            'fourchetteSalaire': salary,
            'select_1': qualification,
            'heureMax': u'',
            'experience': u'INDIFFERENT',
            'dureeEmission': limit_date,
            'secteurActiviteEntreprise1': domain,
            'secteurActiviteEntreprise2': u'',
            'select_2': u'',
            'select_3': u'',
            'langues1': u'',
            'langues2': u'',
            'textfield': u'',
        }

        if place.split('|')[1] == 'DEPARTEMENT':
            place_type, place_number = self.choose_departement(place.split('|')[2], copy.deepcopy(data))

        elif place.split('|')[1] == 'REGION':
            place_type, place_number = self.choose_region(place.split('|')[2], copy.deepcopy(data))

        else:
            place_type = 'FRANCE'
            place_number = '01'

        params = 'A_%s_%s_%s__%s_P_%s_%s_%s_______INDIFFERENT______________%s' % (urllib.quote(metier).replace('%', '$00'),
                                                                                  place_type,
                                                                                  place_number,
                                                                                  contrat,
                                                                                  domain,
                                                                                  salary,
                                                                                  qualification,
                                                                                  limit_date
                                                                                  )

        self.location('http://candidat.pole-emploi.fr/candidat/rechercheoffres/resultats/%s' % params)

        assert self.is_on_page(SearchPage)
        return self.page.iter_job_adverts()

    def choose_region(self, place, data):
        data['select'] = u'10'
        data['radiogroup_0'] = u'REGION'
        data['choixRegion:hiddenelementSubmit'] = u'choixRegion:hiddenelementSubmit'

        self.location('http://candidat.pole-emploi.fr/candidat/rechercheoffres/avancee.recherche',
                      urllib.urlencode(data))

        data2 = {
            't:formdata': 'H4sIAAAAAAAAAOWZwWoUQRCGK8GIZD2IoHjxEIigl944u6vRIJIYoodBxSVn6emt2e040z129ybjxZO+hi+gBnwDIQdvvoMP4EXEkwe7XTfbIEgc0BxqYBjo6ar6v545/PC/+QwLeyvADIoRGn/rPDdo23yXK4HYvjPS0kqTon2EQ6mVvVloXVkDTJsh4xX3JczxCq0zz3pMaIOFzPyzrLRC5SxL/f7l5EuVX7l7/vXteYDawJkd358VXA3Zg2wHhYPZVVf/QU/n/eUX9zpf30LQ8xSew9xeF5KjD/V7xJNM135w74+DM26RrWd+kQu3JbEYLPfRjatL2wetT+c+fJ+HuRRaQitndHGfl+jgbBpOpx1Op913Rqrh2kSig1PTuY3Vrv+t2odGC7S2P85Kaa1vd7A/6ObfXn2cndy//1zd+PdpODSUnWh4bqF2wcHidOHxSrNGoc9iM+mnj5n4KjnihBxxhxxxlxxxjxzxNXLE18kRr5IjvkGEuDVzIFRMV4RMxXVFyFRsV4RMxXdFyFSMV4RMxXlFyFSsV4RMxXtFyFTMV4RMz30l9NxXQs99JfTcV0LPfSXH4b42YePoZbu8kAM0hS/Qsh6gNZMX1sBWbliFrBQhJSjH6jA+YHJUxsnBhh47rX4GF+73GGP75bv9W62li5MABgssfVEIYILak9PA5cIvISkGjfXmocIfuzXN7zgbAAA=',
            place: 'on',
            'validerLeChoixDesRegions': u'',
            'validerLeChoixDesRegions:hiddenelementSubmit': 'validerLeChoixDesRegions:hiddenelementSubmit',
        }

        self.location('http://candidat.pole-emploi.fr/candidat/rechercheoffres/avancee/choisirlesregions.choisirdeslieux',
                      urllib.urlencode(data2))

        return self.decode_place(self.page.url)

    def decode_place(self, url):
        re_url = re.compile('http://candidat.pole-emploi.fr/candidat/rechercheoffres/avancee/A_(.*?)_(.*?)_(.*?)__(.*?)_P_(.*?)_(.*?)_(.*?)_______INDIFFERENT______________(.*?)', re.DOTALL)
        if re_url.match(url):
            return re_url.search(url).group(2), re_url.search(url).group(3)
        else:
            return 'FRANCE', '01'

    def choose_departement(self, place, data):

        data['select'] = u'10'
        data['radiogroup_0'] = u'DEPARTEMENT'
        data['choixDepartement:hiddenelementSubmit'] = u'choixDepartement:hiddenelementSubmit'

        self.location('http://candidat.pole-emploi.fr/candidat/rechercheoffres/avancee.recherche',
                      urllib.urlencode(data))

        data2 = {
            't:formdata': 'H4sIAAAAAAAAAO3dT2sTQRzG8alYkaYHEfTWg1BBL5u2afpHEamW6iFUofQsm82k3bq7s85M2njxpG/DN6AWfAdCD958D74ALyKePDjz1LYjglACVZinEArJ7swvn/bwpQ3M2y9ifK8tWlpm21K7h+r3tTTNdDetMimb97dVbnLdkWZV1qm2spSVNbcKpWqjRaL0VpLWqbsvsWktjdXP20mmtCzyrvte1qry1ycdd/303Ne6f/PB1Td3zwkx1OLSjtskKdJqK3nU3ZGZFSdfw/qshmp9uPHyYevbO+GHeiZeiLG9ZbF4yp3dhdnTrhq63dt/3b2bGpmsdN2TaWbXcln0pjekHdTXNw8an698/HFOjHVEI1OV1apYT0tpxeWOd2p6p+aG1Xm1dftwTisuHu072sgrpx35sVaZNGZj0C1zY3JVHez35vvfX386MTyjn958+Cs1ys7+3vOjMPoFxq2YOHriycwIq/nFJkZ4J5P/jcIsFZzCHBWcQosKTmGeCk6hTQWnsEAFp7BIBaewRAWnsByxQuOkmmKOx4Ah5noMGGLOx4Ah5n4MGGIOyIAh5oIMGGJOyIAh5oYMGGKOyICBFYm/OrEiwcCKBAMrEgysSDCwIsHAigQDKxIMrEgwsCLBwIrEf+1YkWBgRYKBFQkGViQYWJFgYEWCgRUJBlYkGFiRYGBF4lNPrEgwsCLBwIoEAysSDKxIMLAiwcCKBAMrEgysSDCwIj1DmxUJBlYkGFiRYGBFgoEVCQZWJBhYkWBgRYKBFQkGVqRnWGBFgoEVCQZWJBhYkWBgRYKBFQkGViQYWJFgYEWCgRXpGRZZkWBgRYKBFQkGViQYWJFgYEWCgRUJBlYkGFiRYGBFeoYlViQYWJFgYEWCgRUJBlYkGFiRYGBFgoEVCQZWJBhYkZ5hmRUJBlYkGFiRYGBFgoEVCQZWJBhYkWBgRYKBFQmGmCty8phhdibmjAwdYu7I0CHmkAwdYi7J0CHmlAwdYm7J0CHmmAwd/m1NrovOKe/dTYu8J3Xh7lL5sCdNL3jVaLHW10ktkzLzB+6Vg+r4JL4k3y7DQ/juqYFVFQ4CtH8eC7j56v3+nca1qcNTDWWB9f2phn7uC0enGE79mqYj/bTD1d9n/QkhTJ63oXIAAA==',
            place: 'on',
            'validerLeChoixDesDepartements': u'',
            'validerLeChoixDesDepartements:hiddenelementSubmit': 'validerLeChoixDesDepartements:hiddenelementSubmit',

        }

        self.location('http://candidat.pole-emploi.fr/candidat/rechercheoffres/avancee/choisirlesdepartements.choisirdeslieux',
                      urllib.urlencode(data2))

        return self.decode_place(self.page.url)

    @id2url(PopolemploiJobAdvert.id2url)
    def get_job_advert(self, url, advert):
        self.location(url)
        assert self.is_on_page(AdvertPage)
        return self.page.get_job_advert(url, advert)
