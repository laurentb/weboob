"browser for lefigaro website"
# -*- coding: utf-8 -*-

# Copyright(C) 2011  Julien Hebert
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

from .pages.article import ArticlePage
from .pages.flashactu import FlashActuPage
from weboob.tools.browser import BaseBrowser



class NewspaperFigaroBrowser(BaseBrowser):
    "NewspaperFigaroBrowser class"
    PAGES = {
             "http://www.lefigaro.fr/flash-actu/(\d{4})/(\d{2})/(\d{2})/(.*$)": FlashActuPage,
             "http://www.lefigaro.fr/flash-sport/(\d{4})/(\d{2})/(\d{2})/(.*$)": FlashActuPage,
             "http://www.lefigaro.fr/politique/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/sciences/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/sport/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/sport-business/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/football-ligue-1-et-2/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/international/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/livres/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/immobilier/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/actualite-france/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/mon-figaro/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/cinema/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/conjoncture/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/football/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/automobile/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/marches/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/actualites/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/matieres-premieres/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/programmes-tele/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/le-talk/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/sortir-paris/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/vie-entreprise/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/autres-sports/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/environnement/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/rugby/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/societes/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/medias/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/hightech/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/conso/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/theatre/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/football-coupes-d-europe/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/sante/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/assurance/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/retraite/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/tennis/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/emploi/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/impots/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/culture/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/musique/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/photos/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/formation/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/lefigaromagazine/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/creation-gestion-entreprise/(\d{4})/(\d{2})/(\d{2})/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/flash-eco/(\d{4})/(\d{2})/(\d{2})/(.*$)": FlashActuPage,
            }

    def is_logged(self):
        return False

    def login(self):
        pass

    def fillobj(self, obj, fields):
        pass

    def get_content(self, _id):
        "return page article content"
        self.location(_id)
        return self.page.get_article(_id)
