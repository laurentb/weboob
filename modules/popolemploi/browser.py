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
import urllib

from .pages import SearchPage, AdvertPage
from .job import PopolemploiJobAdvert


__all__ = ['PopolemploiBrowser']


class PopolemploiBrowser(BaseBrowser):
    PROTOCOL = 'http'
    DOMAIN = 'http://www.pole-emploi.fr/accueil/'
    ENCODING = None

    PAGES = {
        'http://candidat.pole-emploi.fr/candidat/rechercheoffres/resultats(.*?)': SearchPage,
        'http://candidat.pole-emploi.fr/candidat/rechercheoffres/detail/(?P<id>.+)': AdvertPage,
    }

    def search_job(self, pattern=None, metier=None, place=None, contrat=None):
        if pattern:
            self.location('http://offre.pole-emploi.fr/resultat?offresPartenaires=true&libMetier=%s'
                          % pattern.replace(' ', '+'))
        else:
            data = {
                't:formdata': 'H4sIAAAAAAAAAJVSwUocQRAtJ1HBPSQonoLIEo1BpPeiErJ42AQ8LYlkMRdPPW3N2trT3emu2Vkv3vIb+YIg5Bs85JZ/yAfkmlMO6d5hR0UY1oEZpqtfVb33qr7/gfnyDew7FGfowmuyzKHvDGRulcwk4luuFLoROq94jeIjrgWid3CUOWaR5YIJk+eFZsQtenKXTJ7lMWaNRk2e9aW+GBRpLqk3QvHeaMIx4caRMwK9n9x4L40+/vrj+qDVXksgOYFFUeEIVk7656FrR3E97HxMz1FQtw8tVJiH8h94jgTLdyADclIPu2MHz2OQxSCr8uD2GVtL8GKi8HNQ2Oefpgp7lcJyB7YbvMHwZ2QNCH7sGTdk3PJwqq3YCz44VDJlKffIemkIckGHEtXpxgCpsJvHN63fqz//JTAXREXRzqgo6gtcQTKO3ycEz6p2NcdHk+s9ltyD6dxcn+5mf7/9SoJ3E1ZlG9YbOCiJhY/ABYKn8TADPsKXypfQbsD5MHhB08oL1XGmnKr6Fmw2IOsrF0w7nHXD35mCjK52vGmv5+7v7b0RL922Ll/DqwaOljtCzcN8/dSG1p3Y7NkTQ/4DH0zoXggEAAA=',
                'emploiRecherche': metier,
                'lieu': place,
                'select': contrat,
                'partenaires': 'on',
            }
            self.location('http://candidat.pole-emploi.fr/candidat/rechercheoffres/simplifiee.recherche',
                          urllib.urlencode(data))
        assert self.is_on_page(SearchPage)
        return self.page.iter_job_adverts()

    @id2url(PopolemploiJobAdvert.id2url)
    def get_job_advert(self, url, advert):
        self.location(url)
        assert self.is_on_page(AdvertPage)
        return self.page.get_job_advert(url, advert)
