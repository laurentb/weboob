# -*- coding: utf-8 -*-

# Copyright(C) 2013      Romain Bignon
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

from weboob.deprecated.browser import Browser

from .pages import IndexPage, TrackPage


__all__ = ['ChronopostBrowser']


class ChronopostBrowser(Browser):
    PROTOCOL = 'http'
    DOMAIN = 'www.chronopost.fr'
    ENCODING = None

    PAGES = {
        'http://www.chronopost.fr/transport-express/livraison-colis':  IndexPage,
        'http://www.chronopost.fr/transport-express/livraison-colis/.*accueil/suivi.*':  TrackPage,
    }

    def get_tracking_info(self, _id):
        self.home()

        assert self.is_on_page(IndexPage)
        self.page.track_package(_id)

        assert self.is_on_page(TrackPage)
        return self.page.get_info(_id)
