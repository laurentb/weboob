# -*- coding: utf-8 -*-
# Copyright(C) 2014 Julia Leven
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
from unittest import TestCase
from weboob.tools.browser2.page import URL

class MyMockBrowser:
    BASEURL = "http://weboob.org"

class URLTest(TestCase):
    base = None

    def setUp(self):
        self.url = URL()
	self.base = None;

############################################### TESTS FOR MATCH METHOD #########################################################
    
    # Check that an assert is sent if both base and brower are none 
    def test_match_base_none_browser_none(self):
        self.assertRaises(AssertionError,self.url.match,"http://weboob.org")

    # Check that no assert is raised when browser is none and a base is indeed instanciated when given as a parameter
    def test_match_base_not_none_browser_none(self):
	try:
	    self.url.match("http://weboob.org/news","http://weboob.org")
	except AssertionError:
	    self.fail("Method match returns an AssertionError while base parameter is not none!");

    # Check that none is returned when none of the defined urls is a regex for the given url
    def test_match_url_pasregex_baseurl(self):
	# Init
        self.url.browser = MyMockBrowser()
        self.url.urls = ["http://test.org","http://test2.org"]
	# Test
        res = self.url.match("http://weboob.org/news")
        # Assertions
	self.assertEqual(self.url.browser.BASEURL,"http://weboob.org");
        self.assertIsNone(res)

    # Check that true is returned when one of the defined urls is a regex for the given url
    def test_match_url_regex_baseurl(self):
    	# Init
        self.url.browser = MyMockBrowser()
        self.url.urls = ["http://test.org","http://weboob.org"]
	# Test
        res = self.url.match("http://weboob.org/news")
 	# Assertions
	self.assertEqual(self.url.browser.BASEURL,"http://weboob.org");
        self.assertTrue(res)

    # Successful test with relatives url
    def test_match_url_sans_http(self):
        # Init
        self.url.browser = MyMockBrowser()
        self.url.urls = ["news"]
        # Test
        res = self.url.match("http://weboob.org/news")
        # Assertions
	self.assertEqual(self.url.browser.BASEURL,"http://weboob.org");
        self.assertTrue(res)



    # Unsuccessful test with relatives url
    def test_match_url_sans_http_fail(self):
        # Init
        self.url.browser = MyMockBrowser()
        self.url.urls = ["youtube"]
        # Test
        res = self.url.match("http://weboob.org/news")
        # Assertions
	self.assertEqual(self.url.browser.BASEURL,"http://weboob.org");
        self.assertIsNone(res)

  

	

    
