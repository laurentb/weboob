# -*- coding: utf-8 -*-

# Copyright(C) 2013      Bezleputh
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
from weboob.tools.value import Value


class IndeedTest(BackendTest):
    MODULE = 'indeed'

    def setUp(self):
        if not self.is_backend_configured():
            self.backend.config['limit_date'] = Value(value='any')
            self.backend.config['metier'] = Value(value='informaticien')
            self.backend.config['contrat'] = Value(value='contract')

    def test_indeed_search(self):
        l = list(self.backend.search_job('informaticien'))
        assert len(l)
        advert = self.backend.get_job_advert(l[0].id, l[0])
        self.assertTrue(advert.url, 'URL for announce "%s" not found: %s' % (advert.id, advert.url))

    def test_indeed_advanced_search(self):
        l = list(self.backend.advanced_search_job())
        assert len(l)
        advert = self.backend.get_job_advert(l[0].id, l[0])
        self.assertTrue(advert.url, 'URL for announce "%s" not found: %s' % (advert.id, advert.url))

    def test_indeep_info_from_id(self):
        l = list(self.backend.advanced_search_job())
        assert len(l)
        advert = self.backend.get_job_advert(l[0].id, None)
        self.assertTrue(advert.url, 'URL for announce "%s" not found: %s' % (advert.id, advert.url))
