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

from __future__ import unicode_literals

from weboob.browser.filters.standard import (
    CleanText
)
from weboob.browser.selenium import (
        SeleniumPage, VisibleXPath
)
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable

from selenium.webdriver.common.by import By


class LoginPage(SeleniumPage):

    is_here = VisibleXPath('//h2[text()[contains(.,"Log on to Internet Banking")]]')

    @property
    def logged(self):
        if self.doc.xpath('//p[contains(text(), "You are now being redirected to your Personal Internet Banking.")]'):
            return True
        return False

    def on_load(self):
        for message in self.doc.xpath('//div[contains(@class, "alertBox")]'):
            error_msg = CleanText('.')(message)
            if any(msg in error_msg for msg in ['The username you entered doesn\'t match our records. Please try again.',
                                                'Please enter your memorable answer and password.',
                                                'The information you entered does not match our records. Please try again.',
                                                'mot de passe invalide']):
                raise BrowserIncorrectPassword(error_msg)
            else:
                raise BrowserUnavailable(error_msg)

    def get_error(self):
        for message in self.doc.xpath('//div[contains(@data-dojo-type, "hsbcwidget/alertBox")]'):
            error_msg = CleanText('.')(message)
            if any(msg in error_msg for msg in ['The username you entered doesn\'t match our records. Please try again.',
                                                'Please enter a valid Username.',
                                                'mot de passe invalide']):
                raise BrowserIncorrectPassword(error_msg)
            else:
                raise BrowserUnavailable(error_msg)
            return

    def login(self, login):
        self.driver.find_element_by_name("userid").send_keys(login)
        self.driver.find_element_by_class_name("submit_input").click()

    def get_no_secure_key(self):
        self.driver.find_element_by_xpath('//a[span[contains(text(), "Without Security Device")]]').click()

    def login_w_secure(self, password, secret):
        self.driver.find_element_by_name("memorableAnswer").send_keys(secret)
        if len(password) < 8:
            raise BrowserIncorrectPassword('The password must be at least %d characters' % 8)
        elif len(password) > 8:
            # HSBC only use 6 first and last two from the password
            password = password[:6] + password[-2:]

        elts = self.driver.find_elements(By.XPATH, "//input[@type='password' and contains(@id,'pass')]")
        for elt in elts:
            if elt.get_attribute('disabled') is None and elt.get_attribute('class') == "smallestInput active":
                elt.send_keys(password[int(elt.get_attribute('id')[-1]) - 1])
        self.driver.find_element_by_xpath("//input[@class='submit_input']").click()
