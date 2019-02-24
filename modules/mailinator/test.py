# -*- coding: utf-8 -*-

# Copyright(C) 2013      Vincent A
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


from weboob.tools.test import BackendTest


class MailinatorTest(BackendTest):
    MODULE = 'mailinator'

    def test_mailinator(self):
        t = self.backend.get_thread('qwerty')
        assert t
        assert t.root
        assert t.root.title
        assert t.root.date
        assert t.root.sender
        assert t.root.receivers

        self.backend.fillobj(t.root, ('content',))
        assert t.root.content
