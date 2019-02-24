"browser for taz website"
# -*- coding: utf-8 -*-

# Copyright(C) 2012 Florent Fourcot
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

from .pages import ArticlePage
from weboob.browser.browsers import AbstractBrowser
from weboob.browser.url import URL


class NewspaperTazBrowser(AbstractBrowser):
    "NewspaperTazBrowser class"
    PARENT = 'genericnewspaper'
    BASEURL = 'http://www.taz.de'

    article_page = URL('/.*', ArticlePage)

    def __init__(self, *args, **kwargs):
        self.weboob = kwargs['weboob']
        super(NewspaperTazBrowser, self).__init__(*args, **kwargs)
