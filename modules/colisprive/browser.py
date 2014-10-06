# -*- coding: utf-8 -*-

# Copyright(C) 2014 Florent Fourcot
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
from .pages import TrackPage, ErrorPage


__all__ = ['ColispriveBrowser']


class ColispriveBrowser(Browser):
    PROTOCOL = 'https'
    DOMAIN = 'www.colisprive.com'
    ENCODING = 'utf8'

    PAGES = {'https://www.colisprive.com/moncolis/pages/detailColis.aspx.*': TrackPage,
             'https://www.colisprive.com/moncolis/Default.aspx.*': ErrorPage,
             }

    def get_tracking_info(self, _id):
        self.location('https://www.colisprive.com/moncolis/pages/detailColis.aspx?numColis=%s' % _id)
        if not self.is_on_page(TrackPage):
            return None

        return self.page.get_info(_id)
