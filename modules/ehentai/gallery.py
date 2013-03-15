# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Roger Philibert
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

from weboob.capabilities.gallery import BaseGallery, BaseImage

__all_ = ['EHentaiGallery', 'EHentaiImage']


class EHentaiGallery(BaseGallery):
    def __init__(self, *args, **kwargs):
        BaseGallery.__init__(self, *args, **kwargs)


class EHentaiImage(BaseImage):
    def __init__(self, *args, **kwargs):
        BaseImage.__init__(self, *args, **kwargs)
