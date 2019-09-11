# -*- coding: utf-8 -*-

# Copyright(C) 2012 Kevin Pouget
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

from weboob.browser import AbstractBrowser, URL

from .linebourse_browser import LinebourseAPIBrowser
from .caisseepargne_pages import SmsPage, SmsPageOption


__all__ = ['CaisseEpargneBrowser']


class CaisseEpargneBrowser(AbstractBrowser):
    PARENT = 'caissedepargne'
    PARENT_ATTR = 'package.browser.CaisseEpargne'

    LINEBOURSE_BROWSER = LinebourseAPIBrowser

    sms = URL(
        r'https://www.icgauth.credit-cooperatif.coop/dacswebssoissuer/AuthnRequestServlet',
        SmsPage,
    )
    sms_option = URL(
        r'https://www.icgauth.credit-cooperatif.coop/dacstemplate-SOL/_(?P<unknown>\d+)/index.html\?transactionID=.*',
        SmsPageOption,
    )

    def __init__(self, nuser, *args, **kwargs):
        kwargs['market_url'] = 'https://www.offrebourse.com'
        super(CaisseEpargneBrowser, self).__init__(nuser, *args, **kwargs)
