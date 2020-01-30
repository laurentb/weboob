# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Julien Veyssier
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


from weboob.browser.pages import AbstractPage


class LoginPage(AbstractPage):
    PARENT = 'creditmutuel'
    PARENT_URL = 'login'


class PorPage(AbstractPage):
    PARENT = 'creditmutuel'
    PARENT_URL = 'por'


class DecoupledStatePage(AbstractPage):
    PARENT = 'creditmutuel'
    PARENT_URL = 'decoupled_state'
    BROWSER_ATTR = 'package.browser.CreditMutuelBrowser'


class CancelDecoupled(AbstractPage):
    PARENT = 'creditmutuel'
    PARENT_URL = 'cancel_decoupled'
    BROWSER_ATTR = 'package.browser.CreditMutuelBrowser'
