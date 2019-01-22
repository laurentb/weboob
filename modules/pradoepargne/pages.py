# -*- coding: utf-8 -*-

# Copyright(C) 2012-2019  Budget Insight


from weboob.browser.pages import AbstractPage


class LoginPage(AbstractPage):
    PARENT = 'cmes'
    PARENT_URL = 'login'
    BROWSER_ATTR = 'package.browser.CmesBrowser'
