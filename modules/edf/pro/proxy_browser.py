# -*- coding: utf-8 -*-

# Copyright(C) 2012-2020  Budget Insight

from weboob.browser.switch import SwitchingBrowser

from .browser import EdfproBrowser
from .browser_collectivites import EdfproCollectivitesBrowser


class ProxyBrowser(SwitchingBrowser):
    BROWSERS = {
        'main': EdfproBrowser,
        'collectivites': EdfproCollectivitesBrowser,
    }

    KEEP_SESSION = True

    def set_browser(self, name):
        old_browser = self._browser
        super(ProxyBrowser, self).set_browser(name)
        if old_browser:
            self._browser.response = old_browser.response
            self._browser.url = old_browser.url
