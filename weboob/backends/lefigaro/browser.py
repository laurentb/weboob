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
    PAGES = {
             "http://www.lefigaro.fr/flash-actu/([0-9][0-9][0-9][0-9])/([0-9][0-9])/([0-9][0-9])/(.*$)": FlashActuPage,
             "http://www.lefigaro.fr/flash-sport/([0-9][0-9][0-9][0-9])/([0-9][0-9])/([0-9][0-9])/(.*$)": FlashActuPage,
             "http://www.lefigaro.fr/politique/([0-9][0-9][0-9][0-9])/([0-9][0-9])/([0-9][0-9])/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/football-ligue-1-et-2/([0-9][0-9][0-9][0-9])/([0-9][0-9])/([0-9][0-9])/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/international/([0-9][0-9][0-9][0-9])/([0-9][0-9])/([0-9][0-9])/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/actualite-france/([0-9][0-9][0-9][0-9])/([0-9][0-9])/([0-9][0-9])/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/cinema/([0-9][0-9][0-9][0-9])/([0-9][0-9])/([0-9][0-9])/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/conjoncture/([0-9][0-9][0-9][0-9])/([0-9][0-9])/([0-9][0-9])/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/automobile/([0-9][0-9][0-9][0-9])/([0-9][0-9])/([0-9][0-9])/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/actualites/([0-9][0-9][0-9][0-9])/([0-9][0-9])/([0-9][0-9])/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/matieres-premieres/([0-9][0-9][0-9][0-9])/([0-9][0-9])/([0-9][0-9])/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/le-talk/([0-9][0-9][0-9][0-9])/([0-9][0-9])/([0-9][0-9])/(.*$)": ArticlePage,
             "http://www.lefigaro.fr/flash-eco/([0-9][0-9][0-9][0-9])/([0-9][0-9])/([0-9][0-9])/(.*$)": FlashActuPage,
             #'.*': ArticlePage
            }

    def is_logged(self):
        return False

    def get_content(self, _id):
        url = _id
        self.location(url)
        print self.page
        return self.page.get_article(_id)
