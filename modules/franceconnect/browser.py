# -*- coding: utf-8 -*-

# Copyright(C) 2012-2020  Budget Insight
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals


from weboob.browser import LoginBrowser, URL
from weboob.tools.compat import urlparse

from .pages import AuthorizePage


class FranceConnectBrowser(LoginBrowser):
    """
    france connect urls work only with nss
    """
    BASEURL = 'https://app.franceconnect.gouv.fr'

    authorize = URL(r'/api/v1/authorize', AuthorizePage)

    def fc_call(self, provider, baseurl):
        self.BASEURL = baseurl
        params = {'provider': provider, 'storeFI': 'false'}
        self.location('/call', params=params)

    def fc_redirect(self, url=None):
        self.BASEURL = 'https://app.franceconnect.gouv.fr'
        if url is not None:
            self.location(url)
        self.page.redirect()
        parse_result = urlparse(self.url)
        self.BASEURL = parse_result.scheme + '://' + parse_result.netloc
