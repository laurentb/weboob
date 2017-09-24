# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from __future__ import unicode_literals


from weboob.tools.test import BackendTest


class InfomaniakTest(BackendTest):
    MODULE = 'infomaniak'

    def test_document(self):
        subscriptions = list(self.backend.iter_subscription())
        assert subscriptions

        for sub in subscriptions:
            docs = list(self.backend.iter_documents(sub))
            assert docs

            for doc in docs:
                content = self.backend.download_document(doc)
                assert content
