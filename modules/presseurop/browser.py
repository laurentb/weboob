"browser for presseurop website"
# -*- coding: utf-8 -*-

# Copyright(C) 2012  Florent Fourcot
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

from datetime import date, datetime, time
from .pages import PresseuropPage
from weboob.browser.browsers import AbstractBrowser
from weboob.browser.url import URL


class NewspaperPresseuropBrowser(AbstractBrowser):
    "NewspaperPresseuropBrowser class"
    PARENT = 'genericnewspaper'
    BASEURL = 'http://www.voxeurop.eu'

    presseurop_page = URL("/.*", PresseuropPage)

    def __init__(self, weboob, *args, **kwargs):
        self.weboob = weboob
        super(self.__class__, self).__init__(*args, **kwargs)

    def get_daily_date(self, _id):
        self.location(_id)
        return self.page.get_daily_date()

    def get_daily_infos(self, _id):
        url = "http://www.voxeurop.eu/fr/today/" + _id
        self.location(url)
        title = self.page.get_title()
        article_date = date(*[int(x)
                              for x in _id.split('-')])
        article_time = time(0, 0, 0)
        article_datetime = datetime.combine(article_date, article_time)
        return url, title, article_datetime
