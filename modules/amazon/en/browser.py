# -*- coding: utf-8 -*-

# Copyright(C) 2017      Théo Dorée
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

from ..browser import AmazonBrowser


class AmazonEnBrowser(AmazonBrowser):
    BASEURL = 'https://www.amazon.com'
    CURRENCY = '$'
    LANGUAGE = 'en-US'

    L_SIGNIN = 'Sign in'
    L_LOGIN = 'Login'
    L_SUBSCRIBER = 'Name: (.*) Edit E'

    WRONGPASS_MESSAGE = "Your password is incorrect"
    WRONG_CAPTCHA_RESPONSE = "Enter the characters as they are given in the challenge."
