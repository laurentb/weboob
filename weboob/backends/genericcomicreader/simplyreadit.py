# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Noé Rubinstein
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

from .backend import GenericComicReaderBackend, DisplayPage

__all__ = ['SimplyreaditBackend']

class SimplyreaditBackend(GenericComicReaderBackend):
    NAME = 'simplyreadit'
    DESCRIPTION = 'Simplyreadit manga reading site'
    IMG_SRC_XPATH = "//img[@class='open']/@src"
    PAGE_LIST_XPATH = "(//div[contains(@class,'dropdown_right')]/ul[@class='dropdown'])[1]/li/a/@href"
    PAGE_TO_LOCATION = "%s"
    ID_TO_URL = 'http://www.simplyread.it/reader/read/%s'
    ID_REGEXP = r'[^/]+(?:/[^/]+)*'
    URL_REGEXP = r'.+symplyread.it/reader/read/(%s)' % ID_REGEXP
    PAGES = { r'http://.+\.simplyread.it/reader/read/.+': DisplayPage }
