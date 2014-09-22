# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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


from logging import debug
from weboob.tools.test import BackendTest


class FourChanTest(BackendTest):
    MODULE = 'fourchan'

    def test_new_messages(self):
        tot = 0
        for thread in self.backend.iter_threads():
            thread = self.backend.fillobj(thread, 'root')
            count = 0
            for m in thread.iter_all_messages():
                count += 1
            debug('Count: %s' % count)
            tot += count

        debug('Total messages: %s' % tot)

        count = 0
        for message in self.backend.iter_unread_messages():
            count += 1

        debug('Unread messages: %s' % count)
