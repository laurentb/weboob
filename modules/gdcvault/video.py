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


from weboob.capabilities.video import BaseVideo

import re

__all__ = ['GDCVaultVideo']


class GDCVaultVideo(BaseVideo):
    def __init__(self, *args, **kwargs):
        BaseVideo.__init__(self, *args, **kwargs)
        self.ext = u'flv'

    @classmethod
    def id2url(cls, _id):
        # attempt to enlarge the id namespace to differentiate
        # videos from the same page
        m = re.match('\d+#speaker', _id)
        if m:
            return u'http://www.gdcvault.com/play/%s#speaker' % _id
        m = re.match('\d+#slides', _id)
        if m:
            return u'http://www.gdcvault.com/play/%s#slides' % _id
        return u'http://www.gdcvault.com/play/%s' % _id

