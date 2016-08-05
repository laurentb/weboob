"browser for 20minutes website"
# -*- coding: utf-8 -*-

# Copyright(C) 2011  Julien Hebert
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

from .pages import ArticlePage
from weboob.browser import AbstractBrowser, URL


class Newspaper20minutesBrowser(AbstractBrowser):
    "Newspaper20minutesBrowser class"
    BASEURL = 'http://www.20minutes.fr'
    PARENT = 'genericnewspaper'

    article_page = URL('/.+/?.*', ArticlePage)

    def __init__(self, weboob, *args, **kwargs):
        self.weboob = weboob
        super(self.__class__, self).__init__(*args, **kwargs)
