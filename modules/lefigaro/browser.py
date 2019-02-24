"browser for lefigaro website"
# -*- coding: utf-8 -*-

# Copyright(C) 2011  Julien Hebert
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


class NewspaperFigaroBrowser(AbstractBrowser):
    "NewspaperFigaroBrowser class"
    PARENT = 'genericnewspaper'
    BASEURL = 'http://lefigaro.fr'

    article_page = URL('http://lefigaro.fr/(.*)/(\d{4})/(\d{2})/(\d{2})/(.*$)',
                       'http://\w+.lefigaro.fr/(.*)/(\d{4})/(\d{2})/(\d{2})/(.*$)',
                       'http://\w+.lefigaro.fr/(.*)',
                       ArticlePage)

    def __init__(self, *args, **kwargs):
        self.weboob = kwargs['weboob']
        super(NewspaperFigaroBrowser, self).__init__(*args, **kwargs)
