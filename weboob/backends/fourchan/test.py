# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


from logging import debug
from weboob.tools.test import BackendTest

class FourChanTest(BackendTest):
    BACKEND = 'fourchan'

    def test_new_messages(self):
        tot = 0
        for thread in self.backend.iter_threads():
            thread = self.backend.fillobj(thread, 'root')
            count = 0
            for m in thread.iter_all_messages():
                count += 1
            debug('Count: %s' % count)
            tot += count

        print 'Total messages: %s' % tot

        count = 0
        for message in self.backend.iter_unread_messages():
            count += 1

        print 'Unread messages: %s' % count
